"""Forecast bias correction engine.

Backtests ECMWF IFS predictions against ERA5 reanalysis ground truth over the
last 30 days to compute per-circuit systematic biases, then applies corrections
to the live forecast.

Data sources (both free, no API key):
  ERA5 Archive:         https://archive-api.open-meteo.com/v1/archive
  Historical Forecast:  https://historical-forecast-api.open-meteo.com/v1/forecast
"""
from __future__ import annotations

import asyncio
import logging
import math
import time
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_ERA5_URL = "https://archive-api.open-meteo.com/v1/archive"
_HIST_FCST_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
_HOURLY_VARS = "temperature_2m,precipitation,wind_speed_10m,wind_direction_10m,cloud_cover"

# In-memory cache: key = f"cal:{circuit_id}", value = {"ts": float, "data": dict}
_calibration_cache: Dict[str, Dict[str, Any]] = {}
_CALIBRATION_TTL = 86400  # 24 hours


async def _fetch_hourly(url: str, params: dict) -> Dict[str, Any]:
    """Shared helper — fetch hourly data from an Open-Meteo archive endpoint."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


async def fetch_era5_archive(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    """Fetch ERA5 ground-truth hourly data for a date range."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": _HOURLY_VARS,
        "timezone": "UTC",
        "wind_speed_unit": "kmh",
    }
    return await _fetch_hourly(_ERA5_URL, params)


async def fetch_historical_forecast(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    """Fetch what ECMWF IFS predicted for the same period."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": _HOURLY_VARS,
        "models": "ecmwf_ifs025",
        "timezone": "UTC",
        "wind_speed_unit": "kmh",
    }
    return await _fetch_hourly(_HIST_FCST_URL, params)


def _safe_list(d: dict, key: str) -> list:
    return d.get(key) or []


def _align_series(
    era5_hourly: Dict[str, list],
    fcst_hourly: Dict[str, list],
) -> List[Dict[str, float]]:
    """Inner join ERA5 and forecast on ISO timestamp strings.

    Returns list of aligned pairs. Only includes hours where all variables
    are non-None in both datasets.
    """
    era5_times = _safe_list(era5_hourly, "time")
    fcst_times = _safe_list(fcst_hourly, "time")

    era5_temps = _safe_list(era5_hourly, "temperature_2m")
    era5_precips = _safe_list(era5_hourly, "precipitation")
    era5_winds = _safe_list(era5_hourly, "wind_speed_10m")

    # Historical forecast field names may have model suffix
    def _get_fcst_var(key: str) -> list:
        # Try bare key first (no suffix), then with _ecmwf_ifs025 suffix
        vals = _safe_list(fcst_hourly, key)
        if not vals:
            vals = _safe_list(fcst_hourly, f"{key}_ecmwf_ifs025")
        return vals

    fcst_temps = _get_fcst_var("temperature_2m")
    fcst_precips = _get_fcst_var("precipitation")
    fcst_winds = _get_fcst_var("wind_speed_10m")

    # Build lookup dict for ERA5 by timestamp
    era5_lookup: Dict[str, Dict[str, float]] = {}
    for i, t in enumerate(era5_times):
        temp = era5_temps[i] if i < len(era5_temps) else None
        precip = era5_precips[i] if i < len(era5_precips) else None
        wind = era5_winds[i] if i < len(era5_winds) else None
        if None not in (temp, precip, wind):
            era5_lookup[t] = {
                "era5_temp": float(temp),
                "era5_precip": float(precip),
                "era5_wind": float(wind),
            }

    pairs = []
    for i, t in enumerate(fcst_times):
        if t not in era5_lookup:
            continue
        f_temp = fcst_temps[i] if i < len(fcst_temps) else None
        f_precip = fcst_precips[i] if i < len(fcst_precips) else None
        f_wind = fcst_winds[i] if i < len(fcst_winds) else None
        if None in (f_temp, f_precip, f_wind):
            continue
        pairs.append({
            "time": t,
            "era5_temp": era5_lookup[t]["era5_temp"],
            "fcst_temp": float(f_temp),
            "era5_precip": era5_lookup[t]["era5_precip"],
            "fcst_precip": float(f_precip),
            "era5_wind": era5_lookup[t]["era5_wind"],
            "fcst_wind": float(f_wind),
        })

    return pairs


def _compute_skill_score(
    temp_mae: float,
    precip_mae: float,
    wind_mae: float,
) -> int:
    """Composite skill score 0-100 vs climatological reference MAEs."""
    temp_ref, precip_ref, wind_ref = 3.0, 1.5, 5.0
    skill_temp = max(0.0, 1.0 - temp_mae / temp_ref)
    skill_precip = max(0.0, 1.0 - precip_mae / precip_ref)
    skill_wind = max(0.0, 1.0 - wind_mae / wind_ref)
    composite = (0.40 * skill_temp + 0.35 * skill_precip + 0.25 * skill_wind) * 100
    return int(round(composite))


def _build_correction_summary(
    temp_bias: float,
    precip_ratio: float,
    wind_bias: float,
) -> str:
    """Human-readable correction summary string."""
    temp_str = f"Temp {'+' if temp_bias >= 0 else ''}{temp_bias:.1f}°C"
    ratio_str = f"Rain ×{precip_ratio:.2f}"
    wind_str = f"Wind {'+' if wind_bias >= 0 else ''}{wind_bias:.1f} km/h"
    return f"{temp_str} | {ratio_str} | {wind_str}"


def compute_bias_stats(
    circuit_id: str,
    aligned_pairs: List[Dict[str, float]],
) -> dict:
    """Compute all bias statistics from aligned ERA5 / forecast pairs."""
    n = len(aligned_pairs)
    now_str = datetime.now(timezone.utc).isoformat()

    empty = {
        "circuit_id": circuit_id,
        "computed_at": now_str,
        "backtest_days": 30,
        "sample_count": 0,
        "is_available": False,
        "temp_bias_c": 0.0,
        "temp_mae_c": 0.0,
        "temp_rmse_c": 0.0,
        "precip_ratio": 1.0,
        "precip_mae_mmhr": 0.0,
        "precip_rmse_mmhr": 0.0,
        "wind_bias_kmh": 0.0,
        "wind_mae_kmh": 0.0,
        "wind_rmse_kmh": 0.0,
        "skill_score": 0,
        "correction_summary": "No calibration data",
    }

    if n < 24:  # Need at least 24 paired hours
        return empty

    temp_diffs = [p["fcst_temp"] - p["era5_temp"] for p in aligned_pairs]
    precip_era5 = [p["era5_precip"] for p in aligned_pairs]
    precip_fcst = [p["fcst_precip"] for p in aligned_pairs]
    wind_diffs = [p["fcst_wind"] - p["era5_wind"] for p in aligned_pairs]

    # Temperature stats
    temp_bias = sum(temp_diffs) / n
    temp_mae = sum(abs(d) for d in temp_diffs) / n
    temp_rmse = math.sqrt(sum(d ** 2 for d in temp_diffs) / n)

    # Precipitation stats (ratio-based)
    mean_era5_precip = sum(precip_era5) / n
    mean_fcst_precip = sum(precip_fcst) / n
    if mean_era5_precip >= 0.01:
        precip_ratio = mean_fcst_precip / mean_era5_precip
    else:
        precip_ratio = 1.0  # Not enough rain events to establish ratio

    precip_diffs = [f - e for f, e in zip(precip_fcst, precip_era5)]
    precip_mae = sum(abs(d) for d in precip_diffs) / n
    precip_rmse = math.sqrt(sum(d ** 2 for d in precip_diffs) / n)

    # Wind stats
    wind_bias = sum(wind_diffs) / n
    wind_mae = sum(abs(d) for d in wind_diffs) / n
    wind_rmse = math.sqrt(sum(d ** 2 for d in wind_diffs) / n)

    skill = _compute_skill_score(temp_mae, precip_mae, wind_mae)
    summary = _build_correction_summary(temp_bias, precip_ratio, wind_bias)

    return {
        "circuit_id": circuit_id,
        "computed_at": now_str,
        "backtest_days": 30,
        "sample_count": n,
        "is_available": True,
        "temp_bias_c": round(temp_bias, 2),
        "temp_mae_c": round(temp_mae, 2),
        "temp_rmse_c": round(temp_rmse, 2),
        "precip_ratio": round(precip_ratio, 3),
        "precip_mae_mmhr": round(precip_mae, 3),
        "precip_rmse_mmhr": round(precip_rmse, 3),
        "wind_bias_kmh": round(wind_bias, 2),
        "wind_mae_kmh": round(wind_mae, 2),
        "wind_rmse_kmh": round(wind_rmse, 2),
        "skill_score": skill,
        "correction_summary": summary,
    }


async def get_calibration_for_circuit(
    circuit_id: str,
    latitude: float,
    longitude: float,
    days: int = 30,
) -> dict:
    """Main entry point — returns calibration stats dict (cached 24h).

    On cache miss: fetches ERA5 + historical forecast concurrently, aligns,
    computes bias, caches, returns.
    On any error: returns is_available=False stats (not cached so next call retries).
    """
    cache_key = f"cal:{circuit_id}"
    now_ts = time.time()

    if cache_key in _calibration_cache:
        entry = _calibration_cache[cache_key]
        if now_ts - entry["ts"] < _CALIBRATION_TTL:
            return entry["data"]

    # Date window: yesterday back 30 days (full days only for archive completeness)
    end_dt = datetime.now(timezone.utc).date() - timedelta(days=1)
    start_dt = end_dt - timedelta(days=days)
    start_date = start_dt.isoformat()
    end_date = end_dt.isoformat()

    try:
        era5_raw, hist_raw = await asyncio.gather(
            fetch_era5_archive(latitude, longitude, start_date, end_date),
            fetch_historical_forecast(latitude, longitude, start_date, end_date),
        )
    except Exception as exc:
        logger.warning("Calibration fetch failed for circuit %s: %s", circuit_id, exc)
        return {
            "circuit_id": circuit_id,
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "backtest_days": days,
            "sample_count": 0,
            "is_available": False,
            "temp_bias_c": 0.0,
            "temp_mae_c": 0.0,
            "temp_rmse_c": 0.0,
            "precip_ratio": 1.0,
            "precip_mae_mmhr": 0.0,
            "precip_rmse_mmhr": 0.0,
            "wind_bias_kmh": 0.0,
            "wind_mae_kmh": 0.0,
            "wind_rmse_kmh": 0.0,
            "skill_score": 0,
            "correction_summary": "No calibration data",
        }

    era5_hourly = era5_raw.get("hourly", {})
    hist_hourly = hist_raw.get("hourly", {})

    pairs = _align_series(era5_hourly, hist_hourly)
    stats = compute_bias_stats(circuit_id, pairs)

    # Only cache successful results (is_available=True)
    if stats["is_available"]:
        _calibration_cache[cache_key] = {"ts": now_ts, "data": stats}

    return stats


def apply_bias_correction(forecast_points: list, stats: dict) -> list:
    """Apply bias corrections to a list of ForecastData objects.

    Returns a new list — does NOT mutate originals (uses dataclasses.replace).
    Only applied when is_available=True and sample_count >= 72.
    """
    if not stats.get("is_available") or stats.get("sample_count", 0) < 72:
        return forecast_points

    temp_bias = stats["temp_bias_c"]
    precip_ratio = stats["precip_ratio"]
    wind_bias = stats["wind_bias_kmh"]

    corrected = []
    for fp in forecast_points:
        kwargs = {}

        if fp.temperature_c is not None:
            kwargs["temperature_c"] = round(fp.temperature_c - temp_bias, 2)

        if fp.precipitation_intensity is not None and precip_ratio > 0.01:
            kwargs["precipitation_intensity"] = max(0.0, round(fp.precipitation_intensity / precip_ratio, 3))

        if fp.wind_speed_kmh is not None:
            kwargs["wind_speed_kmh"] = max(0.0, round(fp.wind_speed_kmh - wind_bias, 1))

        corrected.append(replace(fp, **kwargs))

    return corrected
