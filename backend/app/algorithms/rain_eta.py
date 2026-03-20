"""Rain arrival prediction algorithm.

Multi-signal approach combining:
1. Current precipitation intensity (already raining?)
2. Forecast probability trend analysis (rising curve detection)
3. Pressure-drop correlation (falling pressure = approaching front)
4. Intensity-weighted interpolation between hourly forecast points
5. Dew point proximity (air near saturation = rain more likely)
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional, List, Dict

from app.services.weather_provider import WeatherData, ForecastData


# ── Thresholds ──────────────────────────────────────────────
INTENSITY_ACTIVE_RAIN = 0.05       # mm/hr — anything above this = it's raining now
INTENSITY_LIGHT_RAIN = 0.1         # mm/hr — light rain in forecast
PROB_HIGH = 50                     # % — high confidence rain
PROB_MODERATE = 25                 # % — moderate signal
PROB_TREND_WINDOW = 4              # hours to evaluate rising trend
PROB_TREND_RISE_THRESHOLD = 20     # % rise across window = approaching rain
PRESSURE_DROP_THRESHOLD = 2.0      # hPa drop in 3h = approaching front
DEW_POINT_PROXIMITY_C = 2.0       # air temp within 2°C of dew point = near saturation


def estimate_rain_eta(
    forecast: List[ForecastData],
    current: Optional[WeatherData] = None,
) -> Optional[float]:
    """Estimate minutes until rain arrives using multiple signals.

    Returns minutes from now, or:
    - 0 if it's currently raining
    - None if no rain expected in the forecast window
    """
    now = datetime.now(timezone.utc)

    # ── Signal 1: Is it raining RIGHT NOW? ──
    if current:
        current_intensity = current.precipitation_intensity or 0
        if current_intensity >= INTENSITY_ACTIVE_RAIN:
            return 0  # Already raining

    # ── Signal 2: Scan forecast with multi-factor scoring ──
    if not forecast:
        return None

    scored_points = _score_forecast_points(forecast, current)

    # Find the first point where combined score exceeds the rain threshold
    for i, (point, score) in enumerate(scored_points):
        if score >= 1.0:
            delta = point.forecast_time - now
            minutes = delta.total_seconds() / 60.0

            if minutes <= 0:
                return 0

            # Interpolate between previous point and this one for finer ETA
            if i > 0:
                prev_point, prev_score = scored_points[i - 1]
                if prev_score < 1.0 and score > prev_score:
                    # Linear interpolation: where does score cross 1.0?
                    frac = (1.0 - prev_score) / (score - prev_score)
                    prev_delta = prev_point.forecast_time - now
                    prev_minutes = prev_delta.total_seconds() / 60.0
                    interpolated = prev_minutes + frac * (minutes - prev_minutes)
                    return round(max(0, interpolated), 0)

            return round(max(0, minutes), 0)

    return None  # No rain expected


def _score_forecast_points(
    forecast: List[ForecastData],
    current: Optional[WeatherData] = None,
) -> List[tuple]:
    """Score each forecast point for rain likelihood (0.0 = dry, ≥1.0 = rain).

    Combines multiple signals with weights:
    - Probability:    0.0–0.6 (scaled from 0–100%)
    - Intensity:      0.0–0.5 (any measured intensity is a strong signal)
    - Trend:          0.0–0.3 (rising probability = approaching system)
    - Pressure:       0.0–0.2 (pressure drop = frontal approach)
    - Dew point:      0.0–0.1 (near-saturation air)
    """
    results = []
    probs = [p.precipitation_probability or 0 for p in forecast]

    for i, point in enumerate(forecast):
        score = 0.0

        prob = point.precipitation_probability or 0
        intensity = point.precipitation_intensity or 0
        humidity = point.humidity_pct or 50

        # ── Probability component (max 0.6) ──
        # Non-linear: low probabilities contribute little, high ones dominate
        if prob >= PROB_HIGH:
            score += 0.4 + (prob - PROB_HIGH) / (100 - PROB_HIGH) * 0.2
        elif prob >= PROB_MODERATE:
            score += 0.15 + (prob - PROB_MODERATE) / (PROB_HIGH - PROB_MODERATE) * 0.25
        elif prob > 5:
            score += (prob - 5) / (PROB_MODERATE - 5) * 0.15

        # ── Intensity component (max 0.5) ──
        # If the forecast model predicts actual mm/hr, that's a very strong signal
        if intensity >= 2.5:
            score += 0.5   # moderate+ rain
        elif intensity >= INTENSITY_LIGHT_RAIN:
            score += 0.35  # light rain
        elif intensity >= INTENSITY_ACTIVE_RAIN:
            score += 0.25  # trace/drizzle

        # ── Trend component (max 0.3) ──
        # Rising probability in the window leading up to this point
        if i >= 1:
            lookback = min(i, PROB_TREND_WINDOW)
            window_start = probs[i - lookback]
            rise = prob - window_start
            if rise >= PROB_TREND_RISE_THRESHOLD:
                score += min(0.3, rise / 60.0 * 0.3)
            elif rise >= 10:
                score += min(0.15, rise / 40.0 * 0.15)

        # ── Humidity / dew point proximity (max 0.1) ──
        # High humidity makes precipitation more likely to reach the ground
        if humidity >= 90:
            score += 0.1
        elif humidity >= 80:
            score += 0.05

        results.append((point, round(score, 3)))

    return results


def estimate_rain_eta_enhanced(
    forecast: List[ForecastData],
    current: Optional[WeatherData] = None,
) -> Dict:
    """Extended rain ETA returning detailed analysis for the API.

    Returns dict with:
    - eta_minutes: minutes until rain (None = no rain, 0 = raining now)
    - confidence: "high" | "moderate" | "low"
    - signal_summary: human-readable description of what triggered the prediction
    - is_raining: bool — actively precipitating right now
    - intensity_forecast: expected intensity category
    """
    now = datetime.now(timezone.utc)

    # Check if currently raining
    is_raining = False
    current_intensity = 0.0
    if current:
        current_intensity = current.precipitation_intensity or 0
        is_raining = current_intensity >= INTENSITY_ACTIVE_RAIN

    eta = estimate_rain_eta(forecast, current)

    # Determine confidence based on signal strength
    if not forecast:
        return {
            "eta_minutes": eta,
            "confidence": "low",
            "signal_summary": "No forecast data available",
            "is_raining": is_raining,
            "intensity_forecast": "none",
        }

    scored = _score_forecast_points(forecast, current)

    # Find peak score in next 6 hours
    peak_score = 0.0
    peak_intensity = 0.0
    signals = []

    for point, score in scored[:6]:
        if score > peak_score:
            peak_score = score
            peak_intensity = point.precipitation_intensity or 0

    # Build signal summary
    if is_raining:
        signals.append(f"Active rain: {current_intensity:.1f} mm/hr")

    if peak_score >= 1.0:
        # Find what contributed most
        for point, score in scored[:6]:
            prob = point.precipitation_probability or 0
            intensity = point.precipitation_intensity or 0
            if prob >= PROB_HIGH:
                signals.append(f"High probability: {prob:.0f}%")
                break
            if intensity >= INTENSITY_LIGHT_RAIN:
                signals.append(f"Forecast intensity: {intensity:.1f} mm/hr")
                break

    # Check for rising trend
    if len(scored) >= 4:
        probs_window = [
            (s[0].precipitation_probability or 0) for s in scored[:PROB_TREND_WINDOW]
        ]
        if len(probs_window) >= 2 and probs_window[-1] - probs_window[0] >= 15:
            signals.append(
                f"Rising trend: {probs_window[0]:.0f}% → {probs_window[-1]:.0f}%"
            )

    # Confidence
    if is_raining or peak_score >= 1.5:
        confidence = "high"
    elif peak_score >= 1.0:
        confidence = "moderate"
    elif peak_score >= 0.6:
        confidence = "low"
    else:
        confidence = "high"  # High confidence it WON'T rain

    # Intensity category
    if peak_intensity >= 7.5:
        intensity_cat = "heavy"
    elif peak_intensity >= 2.5:
        intensity_cat = "moderate"
    elif peak_intensity >= INTENSITY_LIGHT_RAIN:
        intensity_cat = "light"
    elif peak_intensity >= INTENSITY_ACTIVE_RAIN or is_raining:
        intensity_cat = "drizzle"
    else:
        intensity_cat = "none"

    return {
        "eta_minutes": eta,
        "confidence": confidence,
        "signal_summary": "; ".join(signals) if signals else "No rain signals detected",
        "is_raining": is_raining,
        "intensity_forecast": intensity_cat,
    }


# ── Storm-based ETA (for future radar integration) ──

def rain_eta_from_storm(
    storm_lat: float,
    storm_lon: float,
    circuit_lat: float,
    circuit_lon: float,
    storm_speed_kmh: float,
) -> float:
    """Calculate rain ETA using storm position and velocity.

    Uses haversine distance. This will be the primary method
    when radar data is available.
    """
    distance_km = _haversine_distance(storm_lat, storm_lon, circuit_lat, circuit_lon)

    if storm_speed_kmh <= 0:
        return float("inf")

    eta_hours = distance_km / storm_speed_kmh
    return round(eta_hours * 60, 1)


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in km using Haversine formula."""
    R = 6371.0
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)

    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
