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


def _safe(lst: list, idx: int, default: float = 0.0) -> float:
    """Safely index a list, returning default if out of bounds or None."""
    if idx < len(lst) and lst[idx] is not None:
        return float(lst[idx])
    return default


def _iso_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
