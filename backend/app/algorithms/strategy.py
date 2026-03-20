"""Racing strategy recommendation engine.

Generates tire compound and pit window recommendations based on:
- Track temperature forecast (compound suitability)
- Rain probability timeline (wet tire windows)
- Track drying predictions (intermediate transitions)
- Wind conditions (degradation effects)
"""
from __future__ import annotations

from typing import Optional, List, Dict
from app.services.weather_provider import WeatherData, ForecastData
from app.algorithms.drying_model import classify_track_condition, TRACK_DRY, TRACK_DAMP, TRACK_WET, TRACK_VERY_WET, TRACK_FLOODED


# Tire compound temperature windows (track surface temp in °C)
COMPOUND_WINDOWS = {
    "hypersoft": {"min": 20, "optimal_min": 25, "optimal_max": 35, "max": 40},
    "ultrasoft":  {"min": 22, "optimal_min": 28, "optimal_max": 40, "max": 45},
    "supersoft":  {"min": 25, "optimal_min": 30, "optimal_max": 45, "max": 50},
    "soft":       {"min": 28, "optimal_min": 35, "optimal_max": 50, "max": 55},
    "medium":     {"min": 30, "optimal_min": 38, "optimal_max": 55, "max": 60},
    "hard":       {"min": 35, "optimal_min": 42, "optimal_max": 60, "max": 65},
    "intermediate": {"min": 5, "optimal_min": 10, "optimal_max": 40, "max": 50},
    "wet":        {"min": 5, "optimal_min": 10, "optimal_max": 35, "max": 45},
}


def recommend_compound(
    track_temp_c: float,
    track_condition: str,
    wind_speed_kmh: float = 0,
) -> Dict[str, object]:
    """Recommend tire compound based on conditions.

    Returns:
        primary: Best compound for current conditions
        alternative: Alternative compound
        reason: Explanation
        all_ratings: Rating for each compound (0-100)
    """
    # Wet conditions override
    if track_condition in (TRACK_FLOODED, TRACK_VERY_WET):
        return {
            "primary": "wet",
            "alternative": None,
            "reason": f"Standing water on track ({track_condition}). Full wet tires required.",
            "all_ratings": _rate_wet_conditions("wet"),
        }

    if track_condition == TRACK_WET:
        return {
            "primary": "wet",
            "alternative": "intermediate",
            "reason": "Wet track surface. Consider intermediates if drying.",
            "all_ratings": _rate_wet_conditions("wet_drying"),
        }

    if track_condition == TRACK_DAMP:
        return {
            "primary": "intermediate",
            "alternative": "soft",
            "reason": "Damp conditions. Intermediates optimal, slicks if drying quickly.",
            "all_ratings": _rate_wet_conditions("damp"),
        }

    # Dry conditions — rate each compound
    ratings = {}
    for compound, window in COMPOUND_WINDOWS.items():
        if compound in ("intermediate", "wet"):
            ratings[compound] = 5  # Not suitable for dry
            continue

        if track_temp_c < window["min"] or track_temp_c > window["max"]:
            ratings[compound] = 10
        elif window["optimal_min"] <= track_temp_c <= window["optimal_max"]:
            # In optimal window
            center = (window["optimal_min"] + window["optimal_max"]) / 2
            distance = abs(track_temp_c - center)
            range_half = (window["optimal_max"] - window["optimal_min"]) / 2
            ratings[compound] = round(90 - (distance / max(range_half, 1)) * 20)
        else:
            # In working range but not optimal
            ratings[compound] = 50

        # Wind penalty for softer compounds (higher degradation)
        if wind_speed_kmh > 30 and compound in ("hypersoft", "ultrasoft", "supersoft"):
            ratings[compound] = max(10, ratings[compound] - 10)

    sorted_compounds = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
    primary = sorted_compounds[0][0]
    alternative = sorted_compounds[1][0] if len(sorted_compounds) > 1 else None

    reason = f"Track temp {track_temp_c}°C — {primary} compound in optimal window."
    if wind_speed_kmh > 30:
        reason += f" High wind ({wind_speed_kmh} km/h) may increase degradation."

    return {
        "primary": primary,
        "alternative": alternative,
        "reason": reason,
        "all_ratings": ratings,
    }


def generate_strategy_timeline(
    forecast: List[ForecastData],
    track_temps: List[float],
    surface_type: str = "standard_asphalt",
) -> List[Dict[str, object]]:
    """Generate hour-by-hour strategy recommendations.

    Args:
        forecast: Weather forecast points
        track_temps: Corresponding track temperatures
        surface_type: Circuit surface type

    Returns list of hourly strategy snapshots.
    """
    timeline = []

    for i, (point, track_temp) in enumerate(zip(forecast[:24], track_temps[:24])):
        intensity = point.precipitation_intensity or 0
        prob = point.precipitation_probability or 0
        humidity = point.humidity_pct or 50
        wind = point.wind_speed_kmh or 10

        condition = classify_track_condition(
            precipitation_intensity=intensity,
            precipitation_probability=prob,
            humidity_pct=humidity,
        )

        compound = recommend_compound(
            track_temp_c=track_temp,
            track_condition=condition,
            wind_speed_kmh=wind,
        )

        # Pit window analysis
        pit_recommendation = None
        if i > 0 and len(timeline) > 0:
            prev = timeline[-1]
            # Recommend pit if conditions are changing
            if prev["condition"] != condition:
                if condition in (TRACK_WET, TRACK_VERY_WET) and prev["condition"] == TRACK_DRY:
                    pit_recommendation = "PIT: Rain arriving — switch to wet/intermediate"
                elif condition == TRACK_DAMP and prev["condition"] in (TRACK_WET, TRACK_VERY_WET):
                    pit_recommendation = "PIT WINDOW: Track drying — consider intermediates"
                elif condition == TRACK_DRY and prev["condition"] in (TRACK_DAMP, TRACK_WET):
                    pit_recommendation = "PIT WINDOW: Dry line forming — consider slicks"

        timeline.append({
            "hour": i,
            "forecast_time": point.forecast_time.isoformat(),
            "track_temp_c": round(track_temp, 1),
            "condition": condition,
            "compound": compound["primary"],
            "compound_alternative": compound["alternative"],
            "compound_reason": compound["reason"],
            "rain_probability": round(prob, 0),
            "pit_recommendation": pit_recommendation,
        })

    return timeline


def _rate_wet_conditions(state: str) -> Dict[str, int]:
    """Rate compounds for wet conditions."""
    if state == "wet":
        return {"wet": 95, "intermediate": 40, "hard": 5, "medium": 5, "soft": 5,
                "supersoft": 5, "ultrasoft": 5, "hypersoft": 5}
    elif state == "wet_drying":
        return {"wet": 80, "intermediate": 70, "hard": 10, "medium": 10, "soft": 10,
                "supersoft": 5, "ultrasoft": 5, "hypersoft": 5}
    else:  # damp
        return {"intermediate": 90, "wet": 50, "soft": 45, "medium": 40, "hard": 30,
                "supersoft": 35, "ultrasoft": 25, "hypersoft": 20}
