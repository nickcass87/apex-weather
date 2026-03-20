"""Track grip level estimation model.

Estimates relative grip level (0-100%) based on:
- Track temperature (too cold or too hot reduces grip)
- Surface moisture/condition
- Rubber buildup (session progression)
- Surface type characteristics
- Wind effects on aerodynamic grip
"""
from __future__ import annotations

from typing import Dict, Optional


SURFACE_GRIP_BASE: Dict[str, float] = {
    "standard_asphalt":  85.0,
    "high_grip_asphalt": 92.0,
    "abrasive":          88.0,
    "low_grip_street":   70.0,
    "concrete_mix":      75.0,
}


def estimate_grip_level(
    track_temp_c: float,
    air_temp_c: float,
    humidity_pct: float,
    precipitation_intensity: float = 0,
    wind_speed_kmh: float = 0,
    surface_type: str = "standard_asphalt",
    session_minutes: int = 0,
    track_condition: str = "dry",
) -> Dict[str, object]:
    """Estimate track grip level as a percentage (0-100).

    Returns:
        grip_pct: Overall grip level
        mechanical_grip: Surface grip component
        aero_efficiency: Aerodynamic efficiency (affected by wind)
        factors: Breakdown of contributing factors
    """
    base = SURFACE_GRIP_BASE.get(surface_type, 85.0)

    factors = {}

    # Temperature effect on tire grip
    # Optimal range: 30-45°C track temp
    if track_temp_c < 15:
        temp_factor = 0.7 + (track_temp_c / 15.0) * 0.15
        factors["temperature"] = f"Cold track ({track_temp_c}°C) — significantly reduced grip"
    elif track_temp_c < 30:
        temp_factor = 0.85 + ((track_temp_c - 15) / 15.0) * 0.15
        factors["temperature"] = f"Cool track ({track_temp_c}°C) — below optimal"
    elif track_temp_c <= 50:
        temp_factor = 1.0
        factors["temperature"] = f"Optimal track temp ({track_temp_c}°C)"
    elif track_temp_c <= 60:
        temp_factor = 1.0 - ((track_temp_c - 50) / 10.0) * 0.1
        factors["temperature"] = f"Hot track ({track_temp_c}°C) — increased degradation"
    else:
        temp_factor = 0.85
        factors["temperature"] = f"Extreme heat ({track_temp_c}°C) — thermal degradation"

    # Moisture effect
    if track_condition == "dry":
        moisture_factor = 1.0
        factors["moisture"] = "Dry surface"
    elif track_condition == "damp":
        moisture_factor = 0.65
        factors["moisture"] = "Damp surface — reduced grip"
    elif track_condition == "wet":
        moisture_factor = 0.45
        factors["moisture"] = "Wet surface — significant grip loss"
    elif track_condition == "very_wet":
        moisture_factor = 0.30
        factors["moisture"] = "Very wet — aquaplaning risk"
    else:
        moisture_factor = 0.20
        factors["moisture"] = "Flooded — extreme aquaplaning risk"

    # Rubber buildup (improves grip during session)
    rubber_factor = min(1.0, 0.92 + (session_minutes / 120.0) * 0.08)
    if session_minutes > 0:
        factors["rubber"] = f"{session_minutes}min of running — {'good' if session_minutes > 30 else 'building'} rubber"

    # Humidity effect
    if humidity_pct > 85:
        humidity_factor = 0.95
        factors["humidity"] = f"High humidity ({humidity_pct}%) — slight grip reduction"
    else:
        humidity_factor = 1.0

    # Wind effect on aero grip
    if wind_speed_kmh > 60:
        aero_efficiency = 0.75
    elif wind_speed_kmh > 40:
        aero_efficiency = 0.85
    elif wind_speed_kmh > 20:
        aero_efficiency = 0.93
    else:
        aero_efficiency = 1.0

    # Calculate final grip
    mechanical_grip = base * temp_factor * moisture_factor * rubber_factor * humidity_factor
    overall_grip = mechanical_grip * (0.6 + 0.4 * aero_efficiency)  # 60% mechanical, 40% aero

    return {
        "grip_pct": round(min(100, max(0, overall_grip)), 1),
        "mechanical_grip_pct": round(min(100, max(0, mechanical_grip)), 1),
        "aero_efficiency_pct": round(aero_efficiency * 100, 1),
        "factors": factors,
    }
