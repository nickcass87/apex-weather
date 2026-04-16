"""Track surface drying model.

Estimates drying time after rainfall based on:
- Rain intensity and duration
- Air temperature (higher = faster drying)
- Wind speed (higher = faster evaporation)
- Humidity (lower = faster drying)
- Surface type (porous surfaces drain faster)
- Cloud cover (solar heating accelerates drying)

Returns estimated minutes until track is dry enough for slick tires.
"""
from __future__ import annotations

from typing import Optional, List, Dict
from app.services.weather_provider import WeatherData, ForecastData


# Surface drainage characteristics (minutes per mm of water)
SURFACE_DRAINAGE: Dict[str, Dict[str, float]] = {
    "standard_asphalt":  {"drain_rate": 1.0, "porosity": 0.5},
    "high_grip_asphalt": {"drain_rate": 0.85, "porosity": 0.6},
    "abrasive":          {"drain_rate": 0.7,  "porosity": 0.7},
    "low_grip_street":   {"drain_rate": 1.3,  "porosity": 0.3},
    "concrete_mix":      {"drain_rate": 1.1,  "porosity": 0.4},
}

# Track condition states
TRACK_DRY = "dry"
TRACK_DAMP = "damp"
TRACK_WET = "wet"
TRACK_VERY_WET = "very_wet"
TRACK_FLOODED = "flooded"


def classify_track_condition(
    precipitation_intensity: float,
    precipitation_probability: float,
    humidity_pct: float,
    dew_point_c: Optional[float] = None,
    air_temp_c: Optional[float] = None,
    recent_rain_mm: float = 0.0,
) -> str:
    """Classify current track surface condition.

    Uses current intensity + recent accumulation + atmospheric signals.
    Even trace amounts of rain (0.05 mm/hr) leave a damp surface.
    """
    # Active rain intensity thresholds.
    # FIA red-flag / race-suspension criteria:
    #   >5 mm/hr sustained = standing water / aquaplaning risk → FLOODED
    #   2.5-5 mm/hr = significant standing water → VERY_WET
    #   0.5-2.5 mm/hr = wet racing line → WET
    #   0.05-0.5 mm/hr = damp/slippery → DAMP
    if precipitation_intensity >= 5.0:
        return TRACK_FLOODED
    elif precipitation_intensity >= 2.5:
        return TRACK_VERY_WET
    elif precipitation_intensity >= 0.5:
        return TRACK_WET
    elif precipitation_intensity >= 0.05:
        # Any measurable rain = at least damp
        # 0.05-0.1 mm/hr is drizzle/mist, 0.1+ is light rain
        return TRACK_DAMP if precipitation_intensity < 0.5 else TRACK_WET

    # Recent rain that stopped — track still wet/damp
    if recent_rain_mm >= 2.0:
        return TRACK_WET
    elif recent_rain_mm >= 0.5:
        return TRACK_DAMP

    # High humidity + moderate probability = surface moisture
    if humidity_pct > 92 and precipitation_probability > 20:
        return TRACK_DAMP

    # Check for dew/condensation (air near dew point)
    if dew_point_c is not None and air_temp_c is not None:
        if air_temp_c - dew_point_c < 2.0:
            return TRACK_DAMP

    return TRACK_DRY


def estimate_drying_time(
    current_intensity_mm_hr: float,
    air_temp_c: float,
    wind_speed_kmh: float,
    humidity_pct: float,
    cloud_cover_pct: float = 50,
    surface_type: str = "standard_asphalt",
    rain_duration_minutes: float = 30,
) -> Dict[str, object]:
    """Estimate minutes until track is dry enough for slick tires.

    Returns dict with:
        - dry_minutes: estimated minutes to fully dry
        - damp_minutes: estimated minutes to reach "damp" condition
        - condition: current track condition
        - drying_rate: mm/hour evaporation rate
    """
    surface = SURFACE_DRAINAGE.get(surface_type, SURFACE_DRAINAGE["standard_asphalt"])

    # Estimate standing water depth (mm)
    water_depth = current_intensity_mm_hr * (rain_duration_minutes / 60.0)
    water_depth *= (1.0 - surface["porosity"] * 0.3)  # Some drains away

    # Base evaporation rate (mm/hour)
    # Temperature effect: every 10°C above 15°C doubles evaporation
    temp_factor = max(0.3, 1.0 + (air_temp_c - 15.0) / 20.0)

    # Wind effect: accelerates evaporation
    wind_factor = 1.0 + (wind_speed_kmh / 40.0)

    # Humidity effect: low humidity = faster drying
    humidity_factor = max(0.2, (100.0 - humidity_pct) / 50.0)

    # Solar effect: clear skies = faster drying
    solar_factor = 1.0 + (100.0 - cloud_cover_pct) / 100.0 * 0.5

    # Surface drainage speed
    drain_factor = 1.0 / surface["drain_rate"]

    # Combined evaporation rate (mm/hour)
    evap_rate = 0.5 * temp_factor * wind_factor * humidity_factor * solar_factor * drain_factor
    evap_rate = max(0.1, evap_rate)  # Minimum rate

    # Time calculations
    if water_depth <= 0.05:
        dry_minutes = 0.0
        damp_minutes = 0.0
    else:
        dry_minutes = (water_depth / evap_rate) * 60.0
        damp_minutes = max(0, dry_minutes * 0.4)  # Damp transition at ~40% dry time

    # Determine current condition
    condition = classify_track_condition(
        precipitation_intensity=current_intensity_mm_hr,
        precipitation_probability=0,
        humidity_pct=humidity_pct,
    )

    return {
        "condition": condition,
        "water_depth_mm": round(water_depth, 2),
        "drying_rate_mm_hr": round(evap_rate, 2),
        "damp_minutes": round(damp_minutes, 0),
        "dry_minutes": round(dry_minutes, 0),
        # Individual factors for frontend breakdown
        "temp_factor": round(temp_factor, 2),
        "wind_factor": round(wind_factor, 2),
        "humidity_factor": round(humidity_factor, 2),
        "solar_factor": round(solar_factor, 2),
        "drain_factor": round(drain_factor, 2),
    }


def forecast_track_conditions(
    weather: WeatherData,
    forecast: List[ForecastData],
    surface_type: str = "standard_asphalt",
) -> List[Dict[str, object]]:
    """Forecast track conditions hour-by-hour for the next 24 hours.

    Returns list of hourly condition snapshots.
    """
    conditions = []
    rain_active = False
    rain_start_hour = 0

    # Initialize accumulated rain from CURRENT conditions — don't start at zero
    # if it's already raining. The current precipitation tells us the track is
    # already wet before the forecast window begins.
    current_intensity = weather.precipitation_intensity or 0
    current_humidity = weather.humidity_pct or 50
    current_prob = weather.precipitation_probability or 0

    # Estimate how long it's been raining based on current intensity
    # (conservative: assume at least 30 min of current conditions)
    if current_intensity > 0.05:
        accumulated_rain_mm = current_intensity * 0.5  # 30 min of current rate
        rain_active = True
    elif current_humidity > 92 and current_prob > 20:
        accumulated_rain_mm = 0.1  # Trace moisture
    else:
        accumulated_rain_mm = 0.0

    for i, point in enumerate(forecast[:24]):
        intensity = point.precipitation_intensity or 0
        prob = point.precipitation_probability or 0
        temp = point.temperature_c or 20
        wind = point.wind_speed_kmh or 10
        humidity = point.humidity_pct or 50
        cloud = point.cloud_cover_pct or 50

        # Use the HIGHER of forecast intensity and current intensity for
        # the first hour (forecast may underreport ongoing precipitation)
        if i == 0 and current_intensity > intensity:
            intensity = current_intensity

        # Track rain accumulation — lower threshold to catch drizzle
        if intensity > 0.05 or prob > 50:
            if not rain_active:
                rain_start_hour = i
                rain_active = True
            accumulated_rain_mm += intensity * 1.0  # 1 hour of rain
        else:
            if rain_active:
                rain_active = False
            # Evaporation reduces accumulation
            surface = SURFACE_DRAINAGE.get(surface_type, SURFACE_DRAINAGE["standard_asphalt"])
            temp_factor = max(0.3, 1.0 + (temp - 15.0) / 20.0)
            wind_factor = 1.0 + (wind / 40.0)
            humidity_factor = max(0.2, (100.0 - humidity) / 50.0)
            evap_per_hour = 0.5 * temp_factor * wind_factor * humidity_factor / surface["drain_rate"]
            accumulated_rain_mm = max(0, accumulated_rain_mm - evap_per_hour)

        # Classify condition — use actual intensity (not gated by rain_active)
        # Any measurable precipitation should affect the surface condition
        effective_intensity = intensity if (rain_active or intensity > 0.05) else 0
        condition = classify_track_condition(
            precipitation_intensity=effective_intensity,
            precipitation_probability=prob,
            humidity_pct=humidity,
            air_temp_c=temp,
            recent_rain_mm=accumulated_rain_mm,
        )

        # If there's standing water but no rain, estimate drying
        if not rain_active and accumulated_rain_mm > 0.1:
            drying = estimate_drying_time(
                current_intensity_mm_hr=0,
                air_temp_c=temp,
                wind_speed_kmh=wind,
                humidity_pct=humidity,
                cloud_cover_pct=cloud,
                surface_type=surface_type,
                rain_duration_minutes=(i - rain_start_hour) * 60 if rain_start_hour < i else 30,
            )
            if drying["water_depth_mm"] > 0.5:
                condition = TRACK_WET
            elif drying["water_depth_mm"] > 0.1:
                condition = TRACK_DAMP

        conditions.append({
            "hour": i,
            "forecast_time": point.forecast_time.isoformat(),
            "condition": condition,
            "precipitation_intensity": round(intensity, 2),
            "accumulated_rain_mm": round(accumulated_rain_mm, 2),
        })

    return conditions
