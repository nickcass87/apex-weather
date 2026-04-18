from __future__ import annotations

import logging
import math
import uuid
from typing import List

logger = logging.getLogger(__name__)


def _smooth_wind_forecast(forecast_data: list) -> list:
    """Apply circular-mean smoothing to wind direction/speed across forecast points.

    Uses a 3-point weighted average [0.25, 0.5, 0.25] to reduce single-hour
    spikes (e.g., model interpolation artefacts) while preserving the overall
    directional trend.  Applied in-place on a shallow copy of each point.
    """
    import copy
    if len(forecast_data) < 3:
        return forecast_data

    smoothed = [copy.copy(p) for p in forecast_data]
    weights = [0.25, 0.5, 0.25]

    for i in range(1, len(forecast_data) - 1):
        pts = forecast_data[i - 1 : i + 2]
        dirs = [p.wind_direction_deg or 0 for p in pts]
        speeds = [p.wind_speed_kmh or 0 for p in pts]

        # Circular mean for direction (handles 0/360 wrap-around correctly)
        sin_sum = sum(w * math.sin(math.radians(d)) for w, d in zip(weights, dirs))
        cos_sum = sum(w * math.cos(math.radians(d)) for w, d in zip(weights, dirs))
        smoothed_dir = math.degrees(math.atan2(sin_sum, cos_sum)) % 360

        smoothed_speed = sum(w * s for w, s in zip(weights, speeds))

        smoothed[i].wind_direction_deg = round(smoothed_dir, 0)
        smoothed[i].wind_speed_kmh = round(smoothed_speed, 1)

    return smoothed


def _compute_wet_bulb(temp_c: float, humidity_pct: float) -> float:
    """Stull's empirical wet-bulb formula (accurate within 0.35°C for RH > 5%)."""
    import math
    rh = humidity_pct
    t = temp_c
    wb = (t * math.atan(0.151977 * (rh + 8.313659) ** 0.5)
          + math.atan(t + rh)
          - math.atan(rh - 1.676331)
          + 0.00391838 * rh ** 1.5 * math.atan(0.023101 * rh)
          - 4.686035)
    return round(wb, 1)


def _compute_pressure_trend(forecast_data: list) -> tuple:
    """Compute pressure trend from first 6 forecast hours.

    Returns (trend_label, hpa_per_3h):
        trend_label: "rising", "falling", or "steady"
        hpa_per_3h: rate of change in hPa per 3 hours
    """
    # Need at least 6 hours with pressure data
    pressures_with_hour = [
        (i, fp.pressure_hpa) for i, fp in enumerate(forecast_data[:7])
        if fp.pressure_hpa is not None
    ]
    if len(pressures_with_hour) < 2:
        return "steady", 0.0

    first_hour, first_p = pressures_with_hour[0]
    # Take pressure at ~6 hours
    target_idx = min(len(pressures_with_hour) - 1, 6)
    last_hour, last_p = pressures_with_hour[target_idx]

    if last_hour == first_hour:
        return "steady", 0.0

    # Convert to hPa per 3 hours
    hpa_per_hour = (last_p - first_p) / (last_hour - first_hour)
    hpa_per_3h = round(hpa_per_hour * 3, 2)

    if hpa_per_3h > 1.0:
        trend = "rising"
    elif hpa_per_3h < -1.0:
        trend = "falling"
    else:
        trend = "steady"

    return trend, hpa_per_3h


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.circuit import Circuit
from app.schemas.weather import (
    WeatherResponse, WeatherCurrent, WeatherForecastPoint, AlertOut,
    WindAnalysis, TrackConditionPoint, DryingEstimate,
    GripEstimate, WindForecastPoint, CircuitCorner,
    ModelComparisonResponse, ModelComparison, ModelForecastPoint,
    NowcastResponse, NowcastPoint,
)
from app.services.weather_service import WeatherService
from app.services.open_meteo import fetch_multi_model, fetch_real_weather
from app.services.bias_engine import get_calibration_for_circuit, apply_bias_correction
from app.schemas.weather import CalibrationStats as CalibrationStatsSchema
from app.algorithms.track_temperature import estimate_track_temp_from_forecast
from app.algorithms.confidence import compute_confidence_score
from app.algorithms.wind_analysis import analyze_wind, forecast_wind_analysis, get_circuit_corners, compute_wind_veer
from app.algorithms.drying_model import estimate_drying_time, forecast_track_conditions, classify_track_condition
from app.algorithms.grip_model import estimate_grip_level

router = APIRouter(prefix="/weather", tags=["weather"])

weather_service = WeatherService()


@router.get("/{circuit_id}", response_model=WeatherResponse)
async def get_weather(circuit_id: str, db: Session = Depends(get_db)):
    circuit = db.query(Circuit).filter(Circuit.id == circuit_id).first()
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")

    surface = circuit.surface_type or "standard_asphalt"

    # All circuits → Tomorrow.io (live, accurate).
    # Open-Meteo ECMWF is fallback only if Tomorrow.io is unavailable.
    use_demo = False

    if not weather_service.is_demo_mode:
        try:
            current = await weather_service.get_current_weather(circuit.latitude, circuit.longitude)
            forecast_data = await weather_service.get_forecast(circuit.latitude, circuit.longitude, hours=24)
        except Exception as e:
            logger.warning("Tomorrow.io unavailable for %s, falling back to Open-Meteo: %s", circuit.name, e)
            try:
                current, forecast_data = await fetch_real_weather(circuit.latitude, circuit.longitude, hours=24)
            except Exception as e2:
                logger.warning("Open-Meteo also unavailable for %s: %s", circuit.name, e2)
                current = WeatherService._generate_demo_current(circuit.latitude, circuit.longitude)
                forecast_data = WeatherService._generate_demo_forecast(circuit.latitude, circuit.longitude, 24)
                use_demo = True
    else:
        current = WeatherService._generate_demo_current(circuit.latitude, circuit.longitude)
        forecast_data = WeatherService._generate_demo_forecast(circuit.latitude, circuit.longitude, 24)
        use_demo = True

    # Physical consistency corrections — weather APIs sometimes return internally
    # inconsistent data (e.g. rain with clear-sky cloud cover or high UV index).
    # Correct these before any downstream computation.
    precip = current.precipitation_intensity or 0
    if precip >= 0.05:
        # Rain requires clouds — clamp cloud cover to a minimum of 85%
        if (current.cloud_cover_pct or 0) < 85:
            current.cloud_cover_pct = 85.0
        # UV index should be near-zero when raining (cloud/rain attenuation)
        if (current.uv_index or 0) > 2:
            current.uv_index = max(0.0, (current.uv_index or 0) * 0.1)

    # Apply per-circuit ECMWF bias correction (non-blocking: warm cache hit)
    cal_stats = await get_calibration_for_circuit(
        circuit_id=str(circuit.id),
        latitude=circuit.latitude,
        longitude=circuit.longitude,
    )
    if cal_stats.get("is_available"):
        forecast_data = apply_bias_correction(forecast_data, cal_stats)

    # Compute track temperature with surface type
    track_temp = weather_service.compute_track_temperature(current, surface_type=surface)

    # Compute rain ETA (multi-signal analysis)
    rain_eta = weather_service.compute_rain_eta(forecast_data, current)

    # Generate alerts
    alert_dicts = weather_service.compute_alerts(current, forecast_data)

    # Compute data confidence score
    confidence = compute_confidence_score(
        weather=current,
        forecast=forecast_data,
        is_demo_mode=use_demo,
    )

    # Wet-bulb temperature (Stull's formula)
    wet_bulb = None
    if current.temperature_c is not None and current.humidity_pct is not None:
        wet_bulb = _compute_wet_bulb(current.temperature_c, current.humidity_pct)

    # Dew-point spread (° between air temp and dew point — lower = more humid, fog risk)
    dew_spread = None
    if current.temperature_c is not None and current.dew_point_c is not None:
        dew_spread = round(current.temperature_c - current.dew_point_c, 1)

    # Pressure trend
    pressure_trend_label, pressure_trend_hpa_3h = _compute_pressure_trend(forecast_data)

    # Build response
    current_out = WeatherCurrent(
        circuit_id=circuit.id,
        observed_at=current.observed_at,
        temperature_c=current.temperature_c,
        humidity_pct=current.humidity_pct,
        wind_speed_kmh=current.wind_speed_kmh,
        wind_direction_deg=current.wind_direction_deg,
        wind_gust_kmh=current.wind_gust_kmh,
        precipitation_intensity=current.precipitation_intensity,
        precipitation_probability=current.precipitation_probability,
        cloud_cover_pct=current.cloud_cover_pct,
        visibility_km=current.visibility_km,
        pressure_hpa=current.pressure_hpa,
        uv_index=current.uv_index,
        dew_point_c=current.dew_point_c,
        weather_code=current.weather_code,
        track_temperature_c=track_temp,
        rain_eta_minutes=rain_eta,
        wet_bulb_c=wet_bulb,
        dew_point_spread_c=dew_spread,
        pressure_trend=pressure_trend_label,
        pressure_trend_hpa_3h=pressure_trend_hpa_3h,
    )

    # Build forecast with track temps
    forecast_out = []
    track_temps = []
    for fp in forecast_data:
        ft_track_temp = estimate_track_temp_from_forecast(
            air_temp_c=fp.temperature_c or 20,
            wind_speed_kmh=fp.wind_speed_kmh or 0,
            cloud_cover_pct=fp.cloud_cover_pct or 0,
            humidity_pct=fp.humidity_pct or 50,
            surface_type=surface,
            latitude=circuit.latitude,
            longitude=circuit.longitude,
            forecast_time=fp.forecast_time,
            precipitation_intensity=fp.precipitation_intensity or 0,
            solar_ghi_wm2=fp.solar_ghi_wm2,
        )
        track_temps.append(ft_track_temp)
        forecast_out.append(WeatherForecastPoint(
            forecast_time=fp.forecast_time,
            temperature_c=fp.temperature_c,
            humidity_pct=fp.humidity_pct,
            wind_speed_kmh=fp.wind_speed_kmh,
            wind_direction_deg=fp.wind_direction_deg,
            wind_gust_kmh=fp.wind_gust_kmh,
            precipitation_probability=fp.precipitation_probability,
            precipitation_intensity=fp.precipitation_intensity,
            cloud_cover_pct=fp.cloud_cover_pct,
            weather_code=fp.weather_code,
            track_temperature_c=ft_track_temp,
            dew_point_c=fp.dew_point_c,
            pressure_hpa=fp.pressure_hpa,
            solar_ghi_wm2=fp.solar_ghi_wm2,
            precip_type=fp.precip_type,
        ))

    # Alerts
    alerts_out = [
        AlertOut(
            id=uuid.uuid4(),
            alert_type=a["alert_type"],
            severity=a["severity"],
            message=a["message"],
            created_at=datetime.now(timezone.utc),
            is_active=True,
        )
        for a in alert_dicts
    ]

    # === NEW COMPUTATIONS ===

    # Wind analysis + veer/back trend
    wind_data = analyze_wind(current, circuit.name)
    veer_data = compute_wind_veer(forecast_data)
    wind_analysis_out = WindAnalysis(**wind_data, **veer_data)

    # Wind forecast (built after track conditions so we can include precip overlay)
    # Placeholder — populated after track_conds computed below
    wind_forecast_out = []

    # Circuit corner data for wind map overlay
    raw_corners = get_circuit_corners(circuit.name)
    corners_out = []
    for c in raw_corners:
        lat = c["lat"] if c["lat"] != 0 else circuit.latitude
        lng = c["lng"] if c["lng"] != 0 else circuit.longitude
        corners_out.append(CircuitCorner(
            name=str(c["name"]),
            bearing=float(c["bearing"]),
            lat=float(lat),
            lng=float(lng),
        ))

    # Track conditions forecast
    track_conds = forecast_track_conditions(current, forecast_data, surface)
    track_conditions_out = [TrackConditionPoint(**tc) for tc in track_conds]

    # Smooth wind direction/speed before building the per-hour wind forecast.
    # This removes single-hour model artefacts while preserving genuine trends.
    smoothed_forecast = _smooth_wind_forecast(forecast_data)

    # Wind forecast with precipitation overlay data
    wind_fc = forecast_wind_analysis(smoothed_forecast, circuit.name, track_conditions=track_conds)
    wind_forecast_out = [WindForecastPoint(**wf) for wf in wind_fc]

    # Estimate recent rain accumulation from first few forecast hours
    recent_rain_mm = 0.0
    for fp in forecast_data[:3]:
        fp_intensity = fp.precipitation_intensity or 0
        if fp_intensity > 0.01:
            recent_rain_mm += fp_intensity  # each point = 1 hour

    # Drying estimate (if wet or recent rain detected)
    drying_out = None
    precip = current.precipitation_intensity or 0
    if precip > 0.02 or recent_rain_mm > 0.1 or (current.humidity_pct or 0) > 92:
        drying = estimate_drying_time(
            current_intensity_mm_hr=precip,
            air_temp_c=current.temperature_c or 20,
            wind_speed_kmh=current.wind_speed_kmh or 10,
            humidity_pct=current.humidity_pct or 50,
            cloud_cover_pct=current.cloud_cover_pct or 50,
            surface_type=surface,
        )
        drying_out = DryingEstimate(**drying)

    # Grip estimate — pass recent rain for better surface classification
    track_condition = classify_track_condition(
        precipitation_intensity=precip,
        precipitation_probability=current.precipitation_probability or 0,
        humidity_pct=current.humidity_pct or 50,
        dew_point_c=current.dew_point_c,
        air_temp_c=current.temperature_c,
        recent_rain_mm=recent_rain_mm,
    )
    grip_data = estimate_grip_level(
        track_temp_c=track_temp or 30,
        air_temp_c=current.temperature_c or 20,
        humidity_pct=current.humidity_pct or 50,
        precipitation_intensity=precip,
        wind_speed_kmh=current.wind_speed_kmh or 10,
        surface_type=surface,
        track_condition=track_condition,
    )
    grip_out = GripEstimate(**grip_data)

    return WeatherResponse(
        circuit_id=circuit.id,
        circuit_name=circuit.name,
        surface_type=surface,
        confidence_pct=confidence,
        current=current_out,
        forecast=forecast_out,
        alerts=alerts_out,
        wind_analysis=wind_analysis_out,
        track_conditions=track_conditions_out,
        drying_estimate=drying_out,
        grip=grip_out,
        wind_forecast=wind_forecast_out,
        circuit_corners=corners_out,
    )


@router.get("/{circuit_id}/models", response_model=ModelComparisonResponse)
async def get_model_comparison(circuit_id: str, db: Session = Depends(get_db)):
    """Multi-model forecast comparison from Open-Meteo (ECMWF, GFS, ICON)."""
    circuit = db.query(Circuit).filter(Circuit.id == circuit_id).first()
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")

    raw = await fetch_multi_model(circuit.latitude, circuit.longitude, hours=24)

    models_out = []
    for m in raw.get("models", []):
        points = [ModelForecastPoint(**p) for p in m.get("points", [])]
        models_out.append(ModelComparison(
            model_id=m["model_id"],
            label=m["label"],
            provider=m["provider"],
            color=m["color"],
            points=points,
        ))

    return ModelComparisonResponse(
        fetched_at=raw.get("fetched_at", ""),
        models=models_out,
    )


@router.get("/{circuit_id}/calibration", response_model=CalibrationStatsSchema)
async def get_calibration(circuit_id: str, db: Session = Depends(get_db)):
    """Return 30-day ECMWF IFS vs ERA5 backtest bias stats for a circuit.

    Cached 24h in-memory. First call may take ~2-3s while fetching archive data.
    Returns is_available=False if archive APIs are unreachable.
    """
    circuit = db.query(Circuit).filter(Circuit.id == circuit_id).first()
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")

    stats = await get_calibration_for_circuit(
        circuit_id=str(circuit.id),
        latitude=circuit.latitude,
        longitude=circuit.longitude,
    )
    return stats


@router.get("/{circuit_id}/nowcast")
async def get_nowcast(circuit_id: str, db: Session = Depends(get_db)):
    """1-minute nowcast for the next 60 minutes (Tomorrow.io only, Imola circuit).

    For non-Imola circuits or when Tomorrow.io is unavailable, returns an empty
    nowcast derived from the first hour of the ECMWF forecast.
    """
    circuit = db.query(Circuit).filter(Circuit.id == circuit_id).first()
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")

    is_imola = "Imola" in (circuit.name or "")
    points_out = []
    has_rain = False
    peak_intensity = 0.0
    rain_onset: int | None = None

    if is_imola and not weather_service.is_demo_mode:
        try:
            from app.services.tomorrow_io import TomorrowIOProvider
            provider = TomorrowIOProvider()
            nowcast_points = await provider.get_nowcast(circuit.latitude, circuit.longitude, minutes=60)
            for i, p in enumerate(nowcast_points):
                intensity = p.precipitation_intensity or 0.0
                if intensity > 0.1:
                    has_rain = True
                    peak_intensity = max(peak_intensity, intensity)
                    if rain_onset is None:
                        rain_onset = i
                points_out.append(NowcastPoint(
                    forecast_time=p.forecast_time,
                    temperature_c=p.temperature_c,
                    precipitation_intensity=intensity,
                    precipitation_probability=p.precipitation_probability,
                    wind_speed_kmh=p.wind_speed_kmh,
                    wind_direction_deg=p.wind_direction_deg,
                    cloud_cover_pct=p.cloud_cover_pct,
                    precip_type=p.precip_type,
                ))
        except Exception as e:
            logger.warning("Nowcast fetch failed for %s: %s", circuit.name, e)
            # Fall through to empty response

    return NowcastResponse(
        circuit_id=str(circuit.id),
        circuit_name=circuit.name,
        fetched_at=datetime.now(timezone.utc),
        points=points_out,
        has_rain_60min=has_rain,
        peak_intensity_mmhr=round(peak_intensity, 2),
        rain_onset_minutes=rain_onset,
    )
