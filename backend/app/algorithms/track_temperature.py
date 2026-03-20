"""Track surface temperature estimation model.

Estimates the asphalt surface temperature based on atmospheric conditions
and circuit surface type. Track temperature is typically higher than air
temperature due to solar absorption and lower due to wind cooling and
evaporative effects.

Surface type significantly affects heat absorption:
  - Abrasive surfaces (Bahrain, Yas Marina) absorb more heat, run hotter
  - Street circuits (Monaco, Singapore) have smoother, cooler surfaces
  - High-grip asphalt (COTA, Barcelona) runs slightly hotter than standard
"""
from __future__ import annotations

from typing import Dict

# Surface type thermal characteristics
# solar: multiplier on solar heating (>1 = absorbs more)
# offset: constant temperature offset in degrees C
SURFACE_FACTORS: Dict[str, Dict[str, float]] = {
    "standard_asphalt":  {"solar": 1.0,  "offset": 0.0},
    "high_grip_asphalt": {"solar": 1.15, "offset": 2.0},
    "abrasive":          {"solar": 1.25, "offset": 4.0},
    "low_grip_street":   {"solar": 0.85, "offset": -2.0},
    "concrete_mix":      {"solar": 0.90, "offset": -1.0},
}


def estimate_track_temperature(
    air_temp_c: float,
    solar_radiation_wm2: float,
    wind_speed_kmh: float,
    cloud_cover_pct: float = 0,
    humidity_pct: float = 50,
    surface_type: str = "standard_asphalt",
) -> float:
    """Estimate track surface temperature in Celsius.

    Based on the relationship:
      track_temp = air_temp + solar_heating - wind_cooling - evap_cooling + surface_offset

    Args:
        air_temp_c: Ambient air temperature in Celsius.
        solar_radiation_wm2: Incoming solar radiation in W/m2.
        wind_speed_kmh: Wind speed in km/h.
        cloud_cover_pct: Cloud cover percentage (0-100).
        humidity_pct: Relative humidity percentage (0-100).
        surface_type: Circuit surface type (affects heat absorption).

    Returns:
        Estimated track surface temperature in Celsius.
    """
    surface = SURFACE_FACTORS.get(surface_type, SURFACE_FACTORS["standard_asphalt"])

    # Solar heating: asphalt absorbs ~90% of radiation
    # Coefficient tuned to give roughly +10-20C above air temp in full sun
    solar_heating = solar_radiation_wm2 * 0.03 * surface["solar"]

    # Wind cooling effect: higher wind = more convective cooling
    wind_cooling = wind_speed_kmh * 0.2

    # Evaporative cooling from humidity (wet track cools more)
    evap_cooling = (humidity_pct / 100.0) * 2.0

    track_temp = air_temp_c + solar_heating - wind_cooling - evap_cooling + surface["offset"]

    return round(track_temp, 1)


def estimate_track_temp_from_forecast(
    air_temp_c: float,
    wind_speed_kmh: float,
    cloud_cover_pct: float,
    humidity_pct: float = 50,
    surface_type: str = "standard_asphalt",
) -> float:
    """Simplified version for forecast points without direct solar radiation."""
    # Estimate solar radiation from cloud cover
    clear_sky_radiation = 800.0
    cloud_factor = 1.0 - (cloud_cover_pct / 100.0) * 0.7
    solar_radiation = clear_sky_radiation * cloud_factor

    return estimate_track_temperature(
        air_temp_c=air_temp_c,
        solar_radiation_wm2=solar_radiation,
        wind_speed_kmh=wind_speed_kmh,
        cloud_cover_pct=cloud_cover_pct,
        humidity_pct=humidity_pct,
        surface_type=surface_type,
    )
