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

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.circuit import Circuit
from app.schemas.weather import (
    WeatherResponse, WeatherCurrent, WeatherForecastPoint, AlertOut,
    WindAnalysis, TrackConditionPoint, DryingEstimate, StrategyPoint,
    GripEstimate, WindForecastPoint, CircuitCorner,
    ModelComparisonResponse, ModelComparison, ModelForecastPoint,
)
from app.services.weather_service import WeatherService
from app.services.open_meteo import fetch_multi_model, fetch_real_weather
from app.algorithms.track_temperature import estimate_track_temp_from_forecast
from app.algorithms.confidence import compute_confidence_score
from app.algorithms.wind_analysis import analyze_wind, forecast_wind_analysis, get_circuit_corners
from app.algorithms.drying_model import estimate_drying_time, forecast_track_conditions, classify_track_condition
from app.algorithms.strategy import recommend_compound, generate_strategy_timeline
from app.algorithms.grip_model import estimate_grip_level

router = APIRouter(prefix="/weather", tags=["weather"])

weather_service = WeatherService()


@router.get("/{circuit_id}", response_model=WeatherResponse)
async def get_weather(circuit_id: str, db: Session = Depends(get_db)):
    circuit = db.query(Circuit).filter(Circuit.id == circuit_id).first()
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")

    surface = circuit.surface_type or "standard_asphalt"

    # Imola → Tomorrow.io (highest accuracy, live).
    # All other circuits → Open-Meteo ECMWF IFS (real NWP, free, no API key).
    # No circuit ever receives random/synthetic data.
    is_imola = "Imola" in (circuit.name or "")
    use_demo = False

    if is_imola and not weather_service.is_demo_mode:
        try:
            current = await weather_service.get_current_weather(circuit.latitude, circuit.longitude)
            forecast_data = await weather_service.get_forecast(circuit.latitude, circuit.longitude, hours=24)
        except Exception as e:
            # Tomorrow.io unavailable (rate limit / outage) — fall back to Open-Meteo
            logger.warning("Tomorrow.io unavailable for %s, falling back to Open-Meteo: %s", circuit.name, e)
            current, forecast_data = await fetch_real_weather(circuit.latitude, circuit.longitude, hours=24)
    else:
        # All other circuits: use real ECMWF IFS forecast from Open-Meteo (free, no key)
        try:
            current, forecast_data = await fetch_real_weather(circuit.latitude, circuit.longitude, hours=24)
        except Exception as e:
            logger.warning("Open-Meteo unavailable for %s: %s", circuit.name, e)
            # Last-resort fallback only — smooth synthetic data, never random
            current = WeatherService._generate_demo_current(circuit.latitude, circuit.longitude)
            forecast_data = WeatherService._generate_demo_forecast(circuit.latitude, circuit.longitude, 24)
            use_demo = True

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
        )
        track_temps.append(ft_track_temp)
        forecast_out.append(WeatherForecastPoint(
            forecast_time=fp.forecast_time,
            temperature_c=fp.temperature_c,
            humidity_pct=fp.humidity_pct,
            wind_speed_kmh=fp.wind_speed_kmh,
            wind_direction_deg=fp.wind_direction_deg,
            precipitation_probability=fp.precipitation_probability,
            precipitation_intensity=fp.precipitation_intensity,
            cloud_cover_pct=fp.cloud_cover_pct,
            weather_code=fp.weather_code,
            track_temperature_c=ft_track_temp,
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

    # Wind analysis
    wind_data = analyze_wind(current, circuit.name)
    wind_analysis_out = WindAnalysis(**wind_data)

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

    # Strategy timeline
    strategy = generate_strategy_timeline(forecast_data, track_temps, surface)
    strategy_out = [StrategyPoint(**s) for s in strategy]

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
        strategy_timeline=strategy_out,
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
