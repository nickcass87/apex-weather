"""Open-Meteo multi-model weather forecast service.

Fetches hourly forecasts from multiple NWP models via Open-Meteo's free API
(no API key required). Used for the model comparison panel so race engineers
can see where ECMWF, GFS, and ICON agree or disagree on rain timing.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Models to compare — these are the 3 most-used global NWP models
MODELS = [
    {"id": "ecmwf_ifs025", "label": "ECMWF IFS", "provider": "European Centre", "color": "#5a9dba"},
    {"id": "gfs_seamless", "label": "GFS", "provider": "NOAA (US)", "color": "#d9af42"},
    {"id": "icon_seamless", "label": "ICON", "provider": "DWD (Germany)", "color": "#4aad7c"},
]

HOURLY_VARS = [
    "temperature_2m",
    "precipitation",
    "wind_speed_10m",
    "wind_direction_10m",
    "cloud_cover",
]

BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Simple in-memory cache (same pattern as WeatherService)
_cache: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = 600  # 10 minutes


async def fetch_multi_model(
    latitude: float,
    longitude: float,
    hours: int = 24,
) -> Dict[str, Any]:
    """Fetch forecasts from multiple NWP models via Open-Meteo.

    Returns:
        {
            "fetched_at": "2026-03-21T07:00:00Z",
            "models": [
                {
                    "model_id": "ecmwf_ifs025",
                    "label": "ECMWF IFS",
                    "provider": "European Centre",
                    "color": "#5a9dba",
                    "points": [
                        {"time": "...", "temp_c": 8.0, "precip_mm": 0.1, ...},
                        ...
                    ]
                },
                ...
            ]
        }
    """
    cache_key = f"{latitude},{longitude}"
    now = time.time()

    # Check cache
    if cache_key in _cache:
        entry = _cache[cache_key]
        if now - entry["ts"] < _CACHE_TTL:
            return entry["data"]

    model_ids = [m["id"] for m in MODELS]
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(HOURLY_VARS),
        "models": ",".join(model_ids),
        "forecast_hours": hours,
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning("Open-Meteo API error: %s", e)
        # Return empty result on failure
        return {"fetched_at": _iso_now(), "models": []}

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])

    result_models: List[Dict[str, Any]] = []

    for model_meta in MODELS:
        mid = model_meta["id"]
        suffix = f"_{mid}"

        temps = hourly.get(f"temperature_2m{suffix}", [])
        precips = hourly.get(f"precipitation{suffix}", [])
        winds = hourly.get(f"wind_speed_10m{suffix}", [])
        wind_dirs = hourly.get(f"wind_direction_10m{suffix}", [])
        clouds = hourly.get(f"cloud_cover{suffix}", [])

        points = []
        for i, t in enumerate(times):
            points.append({
                "time": t,
                "temp_c": _safe(temps, i),
                "precip_mm": _safe(precips, i),
                "wind_kmh": _safe(winds, i),
                "wind_dir": _safe(wind_dirs, i),
                "cloud_pct": _safe(clouds, i),
            })

        result_models.append({
            "model_id": mid,
            "label": model_meta["label"],
            "provider": model_meta["provider"],
            "color": model_meta["color"],
            "points": points,
        })

    result = {
        "fetched_at": _iso_now(),
        "models": result_models,
    }

    # Cache
    _cache[cache_key] = {"ts": now, "data": result}

    return result


async def fetch_real_weather(
    latitude: float,
    longitude: float,
    hours: int = 24,
) -> tuple:
    """Fetch real current + forecast weather from Open-Meteo using ECMWF IFS.

    Returns (WeatherData, List[ForecastData]) — the same types used throughout
    the rest of the app, so this is a drop-in replacement for the random demo
    data for any circuit that doesn't have a dedicated provider (Tomorrow.io).

    ECMWF IFS at 9 km resolution is the gold-standard global NWP model and
    is available free of charge via Open-Meteo.
    """
    from datetime import datetime, timezone, timedelta
    from app.services.weather_provider import WeatherData, ForecastData

    cache_key = f"real:{latitude:.4f},{longitude:.4f}"
    now_ts = time.time()

    if cache_key in _cache:
        entry = _cache[cache_key]
        if now_ts - entry["ts"] < _CACHE_TTL:
            raw = entry["data"]
            return _parse_real_weather(raw, latitude, longitude)

    hourly_vars = [
        "temperature_2m", "relative_humidity_2m", "dew_point_2m",
        "precipitation", "precipitation_probability",
        "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m",
        "cloud_cover", "surface_pressure", "visibility", "uv_index",
        "weather_code",
    ]
    current_vars = [
        "temperature_2m", "relative_humidity_2m", "dew_point_2m",
        "precipitation", "wind_speed_10m", "wind_direction_10m",
        "wind_gusts_10m", "cloud_cover", "pressure_msl",
        "weather_code", "uv_index",
    ]
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(hourly_vars),
        "current": ",".join(current_vars),
        "models": "ecmwf_ifs025",   # best global NWP model
        "forecast_hours": hours,
        "wind_speed_unit": "kmh",
        "timezone": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(BASE_URL, params=params)
            resp.raise_for_status()
            raw = resp.json()
    except Exception as e:
        logger.warning("Open-Meteo real-weather fetch failed: %s", e)
        raise

    _cache[cache_key] = {"ts": now_ts, "data": raw}
    return _parse_real_weather(raw, latitude, longitude)


def _parse_real_weather(raw: dict, lat: float, lon: float) -> tuple:
    """Parse Open-Meteo API response into (WeatherData, List[ForecastData])."""
    from datetime import datetime, timezone, timedelta
    from app.services.weather_provider import WeatherData, ForecastData

    # ── Current conditions ──────────────────────────────────────────────────
    cur = raw.get("current", {})
    current = WeatherData(
        observed_at=datetime.now(timezone.utc),
        temperature_c=cur.get("temperature_2m"),
        humidity_pct=cur.get("relative_humidity_2m"),
        wind_speed_kmh=cur.get("wind_speed_10m"),
        wind_direction_deg=cur.get("wind_direction_10m"),
        wind_gust_kmh=cur.get("wind_gusts_10m"),
        precipitation_intensity=cur.get("precipitation", 0.0),
        precipitation_probability=None,   # not in current endpoint
        cloud_cover_pct=cur.get("cloud_cover"),
        visibility_km=None,
        pressure_hpa=cur.get("pressure_msl"),
        uv_index=cur.get("uv_index"),
        dew_point_c=cur.get("dew_point_2m"),
        weather_code=cur.get("weather_code"),
    )

    # First hourly rain probability → precipitation_probability for current
    hourly = raw.get("hourly", {})
    probs = hourly.get("precipitation_probability", [None])
    if probs:
        current.precipitation_probability = probs[0]

    # ── Hourly forecast ─────────────────────────────────────────────────────
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    humidities = hourly.get("relative_humidity_2m", [])
    dew_points = hourly.get("dew_point_2m", [])
    precips = hourly.get("precipitation", [])
    precip_probs = hourly.get("precipitation_probability", [])
    wind_speeds = hourly.get("wind_speed_10m", [])
    wind_dirs = hourly.get("wind_direction_10m", [])
    wind_gusts = hourly.get("wind_gusts_10m", [])
    clouds = hourly.get("cloud_cover", [])
    pressures = hourly.get("surface_pressure", [])
    wx_codes = hourly.get("weather_code", [])

    forecast: list = []
    for i, t in enumerate(times):
        try:
            dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
        except Exception:
            dt = datetime.now(timezone.utc) + timedelta(hours=i)

        forecast.append(ForecastData(
            forecast_time=dt,
            temperature_c=_safe(temps, i),
            humidity_pct=_safe(humidities, i),
            wind_speed_kmh=_safe(wind_speeds, i),
            wind_direction_deg=_safe(wind_dirs, i),
            wind_gust_kmh=_safe(wind_gusts, i),
            precipitation_probability=_safe(precip_probs, i),
            precipitation_intensity=_safe(precips, i),
            cloud_cover_pct=_safe(clouds, i),
            weather_code=int(_safe(wx_codes, i, 0)),
        ))

    return current, forecast


def _safe(lst: list, idx: int, default: float = 0.0) -> float:
    """Safely index a list, returning default if out of bounds or None."""
    if idx < len(lst) and lst[idx] is not None:
        return float(lst[idx])
    return default


def _iso_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
