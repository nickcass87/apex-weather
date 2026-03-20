"""Data confidence scoring algorithm.

Computes a 0-100% confidence score for weather data quality based on
data source, forecast horizon, data completeness, and value plausibility.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List

from app.services.weather_provider import WeatherData, ForecastData


def compute_confidence_score(
    weather: Optional[WeatherData],
    forecast: List[ForecastData],
    is_demo_mode: bool,
) -> int:
    """Compute overall data confidence score (0-100).

    Factors that reduce confidence:
    - Demo mode (no real API data): -40 points
    - Missing critical fields: -5 per field
    - Extreme/implausible values: -5 per extreme
    - Short forecast horizon: -10 if < 12 hours
    - Data staleness: -10 to -15 if observation is old
    """
    score = 100

    # Demo mode penalty — data is synthetic, not from a real provider
    if is_demo_mode:
        score -= 40

    if weather is None:
        return max(0, score - 30)

    # Missing critical fields
    critical_fields = [
        weather.temperature_c,
        weather.humidity_pct,
        weather.wind_speed_kmh,
        weather.precipitation_probability,
        weather.cloud_cover_pct,
    ]
    missing_count = sum(1 for f in critical_fields if f is None)
    score -= missing_count * 5

    # Data staleness check
    if weather.observed_at:
        age_minutes = (datetime.now(timezone.utc) - weather.observed_at).total_seconds() / 60
        if age_minutes > 60:
            score -= 15
        elif age_minutes > 30:
            score -= 10

    # Extreme value checks — implausible readings reduce trust
    if weather.temperature_c is not None and (weather.temperature_c > 55 or weather.temperature_c < -30):
        score -= 5
    if weather.wind_speed_kmh is not None and weather.wind_speed_kmh > 120:
        score -= 5
    if weather.humidity_pct is not None and (weather.humidity_pct > 100 or weather.humidity_pct < 0):
        score -= 5

    # Forecast completeness
    if len(forecast) < 6:
        score -= 20
    elif len(forecast) < 12:
        score -= 10

    return max(0, min(100, score))
