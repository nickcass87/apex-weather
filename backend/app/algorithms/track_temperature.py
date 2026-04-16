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

import math
from datetime import datetime
from typing import Dict, Optional

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


def solar_elevation_angle(lat: float, lon: float, utc_time: datetime) -> float:
    """Calculate the sun's elevation angle above the horizon.

    Uses a simplified astronomical formula based on solar declination
    and hour angle. Accurate to within ~1 degree for our purposes.

    Args:
        lat: Latitude in degrees (positive = north).
        lon: Longitude in degrees (positive = east).
        utc_time: UTC datetime of the observation.

    Returns:
        Solar elevation angle in degrees.
        Positive = above horizon, negative = below horizon.
    """
    # Day of year (1-366)
    day_of_year = utc_time.timetuple().tm_yday

    # Solar declination (angle of sun relative to equatorial plane)
    # Approximation using Spencer's formula simplified
    declination_rad = math.radians(
        23.45 * math.sin(math.radians(360.0 / 365.0 * (day_of_year - 81)))
    )

    # Equation of time correction (minutes) — accounts for Earth's orbital eccentricity
    b = math.radians(360.0 / 365.0 * (day_of_year - 81))
    eot_minutes = (
        9.87 * math.sin(2 * b)
        - 7.53 * math.cos(b)
        - 1.5 * math.sin(b)
    )

    # True solar time in hours
    utc_hours = utc_time.hour + utc_time.minute / 60.0 + utc_time.second / 3600.0
    solar_time = utc_hours + (lon / 15.0) + (eot_minutes / 60.0)

    # Hour angle: 0 at solar noon, negative before, positive after
    hour_angle_rad = math.radians((solar_time - 12.0) * 15.0)

    # Latitude in radians
    lat_rad = math.radians(lat)

    # Solar elevation angle
    sin_elevation = (
        math.sin(lat_rad) * math.sin(declination_rad)
        + math.cos(lat_rad) * math.cos(declination_rad) * math.cos(hour_angle_rad)
    )

    # Clamp to [-1, 1] to avoid domain errors from floating point
    sin_elevation = max(-1.0, min(1.0, sin_elevation))

    elevation_deg = math.degrees(math.asin(sin_elevation))
    return elevation_deg


def estimate_track_temperature(
    air_temp_c: float,
    solar_radiation_wm2: float,
    wind_speed_kmh: float,
    cloud_cover_pct: float = 0,
    humidity_pct: float = 50,
    surface_type: str = "standard_asphalt",
    precipitation_intensity: float = 0.0,
) -> float:
    """Estimate track surface temperature in Celsius.

    Based on the relationship:
      track_temp = air_temp + solar_heating - wind_cooling - evap_cooling + surface_offset

    When precipitation is active, rain water absorbs heat from the surface
    and evaporative cooling further reduces track temperature.

    Args:
        air_temp_c: Ambient air temperature in Celsius.
        solar_radiation_wm2: Incoming solar radiation in W/m2.
        wind_speed_kmh: Wind speed in km/h.
        cloud_cover_pct: Cloud cover percentage (0-100).
        humidity_pct: Relative humidity percentage (0-100).
        surface_type: Circuit surface type (affects heat absorption).
        precipitation_intensity: Rain intensity in mm/hr (0 = dry).

    Returns:
        Estimated track surface temperature in Celsius.
    """
    surface = SURFACE_FACTORS.get(surface_type, SURFACE_FACTORS["standard_asphalt"])

    # Solar heating: asphalt absorbs ~90% of radiation
    # Coefficient tuned to give roughly +10-20C above air temp in full sun
    solar_heating = solar_radiation_wm2 * 0.03 * surface["solar"]

    # Precipitation cooling: rain on asphalt dramatically reduces surface temp
    if precipitation_intensity > 0:
        if precipitation_intensity > 5.0:
            # Heavy rain: track is fully saturated, temp drops below air temp
            solar_heating = 0.0
            rain_cooling = 2.0
        elif precipitation_intensity > 1.0:
            # Moderate rain: almost no solar heating, slight evap cooling
            solar_heating *= 0.05
            rain_cooling = 1.0
        else:
            # Light rain (0-1 mm/hr): significantly reduces solar heating
            solar_heating *= 0.20
            rain_cooling = 1.0 + precipitation_intensity
    else:
        rain_cooling = 0.0

    # Wind cooling effect: convective heat loss from asphalt surface.
    # Physical basis: ~10 W/m²·°C convective coefficient at 10 m/s (36 km/h),
    # which translates to roughly 0.09°C cooling per km/h of wind speed.
    # Previous value of 0.2 overcooled by ~2x vs real-world F1 telemetry comparisons.
    wind_cooling = wind_speed_kmh * 0.09

    # Evaporative cooling — only meaningful on a wet/damp surface.
    # On a dry track, ambient humidity does not directly cool the asphalt.
    # Apply full effect when raining, 20% on a dry surface (residual moisture / boundary layer).
    if precipitation_intensity > 0.05:
        evap_cooling = (humidity_pct / 100.0) * 2.5  # wet surface: full evap cooling
    else:
        evap_cooling = (humidity_pct / 100.0) * 0.5  # dry surface: minimal effect

    track_temp = (
        air_temp_c
        + solar_heating
        - wind_cooling
        - evap_cooling
        - rain_cooling
        + surface["offset"]
    )

    return round(track_temp, 1)


def estimate_track_temp_from_forecast(
    air_temp_c: float,
    wind_speed_kmh: float,
    cloud_cover_pct: float,
    humidity_pct: float = 50,
    surface_type: str = "standard_asphalt",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    forecast_time: Optional[datetime] = None,
    precipitation_intensity: float = 0.0,
    solar_ghi_wm2: Optional[float] = None,
) -> float:
    """Estimate track temp for a forecast point, with solar position awareness.

    When latitude, longitude, and forecast_time are provided, the solar
    elevation angle is used to scale clear-sky radiation realistically.
    At night (sun below horizon), solar radiation is 0 — no phantom heating.

    Falls back to the old fixed 800 W/m2 model if location/time not provided,
    for backward compatibility.

    Args:
        air_temp_c: Forecast air temperature in Celsius.
        wind_speed_kmh: Forecast wind speed in km/h.
        cloud_cover_pct: Forecast cloud cover percentage (0-100).
        humidity_pct: Forecast humidity percentage (0-100).
        surface_type: Circuit surface type.
        latitude: Circuit latitude (required for solar position).
        longitude: Circuit longitude (required for solar position).
        forecast_time: UTC datetime of the forecast point.
        precipitation_intensity: Rain intensity in mm/hr (0 = dry).

    Returns:
        Estimated track surface temperature in Celsius.
    """
    # If the provider supplies a direct GHI measurement, use it directly — it's
    # more accurate than our estimated solar model.
    if solar_ghi_wm2 is not None:
        return estimate_track_temperature(
            air_temp_c=air_temp_c,
            solar_radiation_wm2=solar_ghi_wm2,
            wind_speed_kmh=wind_speed_kmh,
            cloud_cover_pct=cloud_cover_pct,
            humidity_pct=humidity_pct,
            surface_type=surface_type,
            precipitation_intensity=precipitation_intensity,
        )

    clear_sky_radiation = 800.0

    if latitude is not None and longitude is not None and forecast_time is not None:
        # Use actual solar position to determine radiation
        elevation = solar_elevation_angle(latitude, longitude, forecast_time)
        if elevation <= 0:
            # Sun is below the horizon — no solar radiation
            solar_radiation = 0.0
        else:
            # Scale by sin(elevation) — low sun = less energy per m2
            solar_factor = math.sin(math.radians(elevation))
            cloud_factor = 1.0 - (cloud_cover_pct / 100.0) * 0.7
            solar_radiation = clear_sky_radiation * solar_factor * cloud_factor
    else:
        # Fallback: no time-of-day awareness (legacy behavior)
        cloud_factor = 1.0 - (cloud_cover_pct / 100.0) * 0.7
        solar_radiation = clear_sky_radiation * cloud_factor

    return estimate_track_temperature(
        air_temp_c=air_temp_c,
        solar_radiation_wm2=solar_radiation,
        wind_speed_kmh=wind_speed_kmh,
        cloud_cover_pct=cloud_cover_pct,
        humidity_pct=humidity_pct,
        surface_type=surface_type,
        precipitation_intensity=precipitation_intensity,
    )
