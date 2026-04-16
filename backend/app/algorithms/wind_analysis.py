"""Wind analysis for motorsport circuits.

Decomposes wind vectors into racing-relevant components:
- Headwind/tailwind along main straight
- Crosswind components
- Gust analysis for car stability
- Wind chill for driver/tire considerations
"""
from __future__ import annotations

import math
from typing import Optional, Dict, List

from app.services.weather_provider import WeatherData, ForecastData


# Main straight bearings for known circuits (degrees from north)
# This represents the direction of travel on the main straight
CIRCUIT_STRAIGHT_BEARINGS: Dict[str, float] = {
    "Spa-Francorchamps": 330,  # NNW direction on Kemmel straight
    "Silverstone": 165,  # SSE on Wellington straight
    "Suzuka": 225,  # SW on main straight
    "Monza": 160,  # SSE on start/finish
    "Imola": 290,  # WNW on main straight
    "Barcelona-Catalunya": 225,  # SW on main straight
    "Red Bull Ring": 340,  # NNW on main straight
    "Monaco": 45,  # NE along harbour
    "Circuit of the Americas": 200,  # SSW on main straight
    "Interlagos": 260,  # W on main straight
    "Bahrain International Circuit": 180,  # S on main straight
    "Yas Marina": 225,  # SW on main straight
    "Singapore Marina Bay": 135,  # SE on main straight
    "Le Mans Circuit de la Sarthe": 210,  # SSW on Mulsanne straight
    "Daytona Road Course": 225,  # SW on main straight
    "Bathurst Mount Panorama": 15,  # NNE on Conrod straight
    "Nürburgring GP": 260,  # W on main straight
    "Brands Hatch": 135,  # SE on main straight
    "Portimão Algarve": 270,  # W on main straight
    "Laguna Seca": 315,  # NW on main straight
    "Hungaroring": 180,  # S on main straight
    "Zandvoort": 135,  # SE on main straight
    "Jeddah Corniche Circuit": 330,  # NNW on main straight
    "Lusail Circuit": 0,  # N on main straight
    "Fuji Speedway": 270,  # W on main straight
    "Mugello": 340,  # NNW on main straight
    "Paul Ricard": 270,  # W on Mistral straight
    "Sebring Raceway": 315,  # NW on main straight
    "Road America": 270,  # W on main straight
    "Watkins Glen": 180,  # S on main straight
}


# Per-corner data for key circuits: name, bearing (direction of travel), lat, lng
# Allows per-corner headwind/tailwind decomposition on the map
CIRCUIT_CORNERS: Dict[str, List[Dict[str, object]]] = {
    "Spa-Francorchamps": [
        {"name": "La Source", "bearing": 150, "lat": 50.4370, "lng": 5.9725},
        {"name": "Eau Rouge", "bearing": 110, "lat": 50.4340, "lng": 5.9705},
        {"name": "Raidillon", "bearing": 35, "lat": 50.4325, "lng": 5.9735},
        {"name": "Kemmel Straight", "bearing": 60, "lat": 50.4330, "lng": 5.9790},
        {"name": "Les Combes", "bearing": 260, "lat": 50.4345, "lng": 5.9845},
        {"name": "Rivage", "bearing": 215, "lat": 50.4325, "lng": 5.9815},
        {"name": "Pouhon", "bearing": 240, "lat": 50.4295, "lng": 5.9745},
        {"name": "Stavelot", "bearing": 310, "lat": 50.4278, "lng": 5.9700},
        {"name": "Blanchimont", "bearing": 350, "lat": 50.4315, "lng": 5.9665},
        {"name": "Bus Stop", "bearing": 10, "lat": 50.4358, "lng": 5.9690},
    ],
    "Silverstone": [
        {"name": "Copse", "bearing": 190, "lat": 52.0700, "lng": -1.0110},
        {"name": "Maggotts", "bearing": 250, "lat": 52.0685, "lng": -1.0180},
        {"name": "Becketts", "bearing": 290, "lat": 52.0690, "lng": -1.0215},
        {"name": "Hangar Straight", "bearing": 320, "lat": 52.0720, "lng": -1.0265},
        {"name": "Stowe", "bearing": 10, "lat": 52.0745, "lng": -1.0240},
        {"name": "Club", "bearing": 90, "lat": 52.0755, "lng": -1.0195},
        {"name": "Abbey", "bearing": 135, "lat": 52.0765, "lng": -1.0130},
        {"name": "Luffield", "bearing": 225, "lat": 52.0720, "lng": -1.0065},
        {"name": "Woodcote", "bearing": 160, "lat": 52.0715, "lng": -1.0110},
    ],
    "Monza": [
        {"name": "Rettifilo", "bearing": 340, "lat": 45.6250, "lng": 9.2910},
        {"name": "Curva Grande", "bearing": 130, "lat": 45.6230, "lng": 9.2975},
        {"name": "Roggia", "bearing": 200, "lat": 45.6200, "lng": 9.2955},
        {"name": "Lesmo 1", "bearing": 230, "lat": 45.6180, "lng": 9.2920},
        {"name": "Lesmo 2", "bearing": 250, "lat": 45.6168, "lng": 9.2885},
        {"name": "Ascari", "bearing": 280, "lat": 45.6155, "lng": 9.2840},
        {"name": "Parabolica", "bearing": 340, "lat": 45.6185, "lng": 9.2810},
        {"name": "Main Straight", "bearing": 345, "lat": 45.6220, "lng": 9.2870},
    ],
    "Monaco": [
        {"name": "Ste Devote", "bearing": 320, "lat": 43.7368, "lng": 7.4210},
        {"name": "Massenet", "bearing": 80, "lat": 43.7385, "lng": 7.4215},
        {"name": "Casino", "bearing": 130, "lat": 43.7392, "lng": 7.4245},
        {"name": "Mirabeau", "bearing": 190, "lat": 43.7388, "lng": 7.4262},
        {"name": "Grand Hotel", "bearing": 245, "lat": 43.7370, "lng": 7.4255},
        {"name": "Tunnel", "bearing": 135, "lat": 43.7358, "lng": 7.4220},
        {"name": "Nouvelle Chicane", "bearing": 215, "lat": 43.7340, "lng": 7.4205},
        {"name": "Tabac", "bearing": 280, "lat": 43.7338, "lng": 7.4185},
        {"name": "Swimming Pool", "bearing": 310, "lat": 43.7342, "lng": 7.4168},
        {"name": "La Rascasse", "bearing": 10, "lat": 43.7350, "lng": 7.4178},
    ],
    "Suzuka": [
        {"name": "Turn 1-2", "bearing": 280, "lat": 34.8462, "lng": 136.5405},
        {"name": "S-Curves", "bearing": 310, "lat": 34.8472, "lng": 136.5370},
        {"name": "Dunlop", "bearing": 260, "lat": 34.8475, "lng": 136.5340},
        {"name": "Degner 1", "bearing": 200, "lat": 34.8462, "lng": 136.5318},
        {"name": "Degner 2", "bearing": 160, "lat": 34.8445, "lng": 136.5320},
        {"name": "Hairpin", "bearing": 70, "lat": 34.8425, "lng": 136.5330},
        {"name": "Spoon", "bearing": 40, "lat": 34.8418, "lng": 136.5395},
        {"name": "130R", "bearing": 75, "lat": 34.8432, "lng": 136.5425},
        {"name": "Casio Triangle", "bearing": 350, "lat": 34.8442, "lng": 136.5440},
    ],
    "Circuit of the Americas": [
        {"name": "Turn 1", "bearing": 310, "lat": 30.1372, "lng": -97.6362},
        {"name": "Esses (T3-6)", "bearing": 220, "lat": 30.1365, "lng": -97.6410},
        {"name": "Turn 7-8", "bearing": 180, "lat": 30.1345, "lng": -97.6430},
        {"name": "Turn 11", "bearing": 120, "lat": 30.1318, "lng": -97.6425},
        {"name": "Turn 12", "bearing": 70, "lat": 30.1308, "lng": -97.6400},
        {"name": "Turn 15", "bearing": 50, "lat": 30.1330, "lng": -97.6340},
        {"name": "Turn 16-18", "bearing": 320, "lat": 30.1342, "lng": -97.6378},
        {"name": "Turn 19-20", "bearing": 350, "lat": 30.1358, "lng": -97.6385},
    ],
    "Barcelona-Catalunya": [
        {"name": "Elf", "bearing": 110, "lat": 41.5720, "lng": 2.2615},
        {"name": "Renault", "bearing": 170, "lat": 41.5705, "lng": 2.2650},
        {"name": "Repsol", "bearing": 240, "lat": 41.5690, "lng": 2.2620},
        {"name": "Seat", "bearing": 270, "lat": 41.5685, "lng": 2.2585},
        {"name": "Campsa", "bearing": 340, "lat": 41.5695, "lng": 2.2555},
        {"name": "La Caixa", "bearing": 15, "lat": 41.5710, "lng": 2.2545},
        {"name": "Banc de Sabadell", "bearing": 50, "lat": 41.5718, "lng": 2.2565},
        {"name": "New Chicane", "bearing": 85, "lat": 41.5715, "lng": 2.2590},
    ],
    "Bahrain International Circuit": [
        {"name": "Turn 1", "bearing": 130, "lat": 26.0340, "lng": 50.5130},
        {"name": "Turn 4", "bearing": 230, "lat": 26.0325, "lng": 50.5145},
        {"name": "Turn 5-6-7", "bearing": 320, "lat": 26.0315, "lng": 50.5120},
        {"name": "Turn 8", "bearing": 0, "lat": 26.0330, "lng": 50.5105},
        {"name": "Turn 10", "bearing": 110, "lat": 26.0350, "lng": 50.5110},
        {"name": "Turn 11", "bearing": 200, "lat": 26.0338, "lng": 50.5135},
        {"name": "Turn 13", "bearing": 160, "lat": 26.0348, "lng": 50.5145},
        {"name": "Turn 14", "bearing": 200, "lat": 26.0355, "lng": 50.5142},
    ],
    "Imola": [
        {"name": "Tamburello", "bearing": 100, "lat": 44.3445, "lng": 11.7210},
        {"name": "Villeneuve", "bearing": 200, "lat": 44.3430, "lng": 11.7230},
        {"name": "Tosa", "bearing": 250, "lat": 44.3420, "lng": 11.7200},
        {"name": "Piratella", "bearing": 300, "lat": 44.3432, "lng": 11.7170},
        {"name": "Acque Minerali", "bearing": 170, "lat": 44.3445, "lng": 11.7155},
        {"name": "Variante Alta", "bearing": 90, "lat": 44.3425, "lng": 11.7135},
        {"name": "Rivazza 1", "bearing": 120, "lat": 44.3415, "lng": 11.7160},
        {"name": "Rivazza 2", "bearing": 60, "lat": 44.3418, "lng": 11.7185},
    ],
    "Red Bull Ring": [
        {"name": "Turn 1", "bearing": 310, "lat": 47.2225, "lng": 14.7650},
        {"name": "Turn 2", "bearing": 265, "lat": 47.2235, "lng": 14.7625},
        {"name": "Turn 3", "bearing": 205, "lat": 47.2230, "lng": 14.7595},
        {"name": "Turn 4", "bearing": 150, "lat": 47.2215, "lng": 14.7588},
        {"name": "Turn 5-6", "bearing": 95, "lat": 47.2200, "lng": 14.7600},
        {"name": "Turn 7", "bearing": 45, "lat": 47.2198, "lng": 14.7625},
        {"name": "Turn 8-9", "bearing": 350, "lat": 47.2205, "lng": 14.7645},
        {"name": "Turn 10", "bearing": 340, "lat": 47.2215, "lng": 14.7655},
    ],
    "Hungaroring": [
        {"name": "Turn 1", "bearing": 150, "lat": 47.5840, "lng": 19.2525},
        {"name": "Turn 2", "bearing": 210, "lat": 47.5830, "lng": 19.2538},
        {"name": "Turn 3", "bearing": 250, "lat": 47.5825, "lng": 19.2520},
        {"name": "Turn 4", "bearing": 345, "lat": 47.5835, "lng": 19.2500},
        {"name": "Turn 5-6", "bearing": 50, "lat": 47.5845, "lng": 19.2495},
        {"name": "Turn 7-8", "bearing": 130, "lat": 47.5850, "lng": 19.2510},
        {"name": "Turn 11", "bearing": 220, "lat": 47.5838, "lng": 19.2545},
        {"name": "Turn 12-13", "bearing": 310, "lat": 47.5842, "lng": 19.2555},
        {"name": "Turn 14", "bearing": 0, "lat": 47.5848, "lng": 19.2540},
    ],
    "Singapore Marina Bay": [
        {"name": "Turn 1", "bearing": 190, "lat": 1.2930, "lng": 103.8640},
        {"name": "Turn 3", "bearing": 260, "lat": 1.2918, "lng": 103.8635},
        {"name": "Turn 5", "bearing": 310, "lat": 1.2922, "lng": 103.8610},
        {"name": "Turn 7", "bearing": 40, "lat": 1.2935, "lng": 103.8595},
        {"name": "Turn 10", "bearing": 115, "lat": 1.2945, "lng": 103.8615},
        {"name": "Turn 14", "bearing": 170, "lat": 1.2940, "lng": 103.8655},
        {"name": "Turn 17", "bearing": 230, "lat": 1.2928, "lng": 103.8658},
        {"name": "Turn 19-20", "bearing": 340, "lat": 1.2935, "lng": 103.8645},
    ],
}


def get_circuit_corners(circuit_name: str) -> List[Dict[str, object]]:
    """Return corner/sector data for a circuit.

    If the circuit has detailed corner data, return it.
    Otherwise, return a single point for the main straight.
    """
    if circuit_name in CIRCUIT_CORNERS:
        return CIRCUIT_CORNERS[circuit_name]

    # Fallback: just return main straight bearing as a single point
    bearing = CIRCUIT_STRAIGHT_BEARINGS.get(circuit_name, 0)
    return [{"name": "Main Straight", "bearing": bearing, "lat": 0, "lng": 0}]


def decompose_wind(
    wind_speed_kmh: float,
    wind_direction_deg: float,
    straight_bearing_deg: float,
) -> Dict[str, float]:
    """Decompose wind into headwind/tailwind and crosswind components.

    Wind direction is where wind comes FROM (meteorological convention).
    Straight bearing is the direction of car travel.

    Returns:
        headwind_kmh: Positive = headwind (opposing car), negative = tailwind
        crosswind_kmh: Absolute crosswind component
        crosswind_direction: "left" or "right" relative to direction of travel
        effective_angle_deg: Wind angle relative to car direction
    """
    # Convert wind "from" direction to wind "going to" direction
    wind_to_deg = (wind_direction_deg + 180) % 360

    # Angle between wind direction and straight direction
    relative_angle = math.radians(wind_to_deg - straight_bearing_deg)

    # Headwind component (positive = opposing car motion)
    headwind = -wind_speed_kmh * math.cos(relative_angle)

    # Crosswind component
    crosswind = wind_speed_kmh * math.sin(relative_angle)

    # Determine crosswind direction
    cross_dir = "left" if crosswind > 0 else "right"

    return {
        "headwind_kmh": round(headwind, 1),
        "crosswind_kmh": round(abs(crosswind), 1),
        "crosswind_direction": cross_dir,
        "effective_angle_deg": round(math.degrees(relative_angle) % 360, 1),
    }


def analyze_wind(
    weather: WeatherData,
    circuit_name: str,
) -> Dict[str, object]:
    """Full wind analysis for a circuit.

    Returns comprehensive wind data including:
    - Raw wind data
    - Decomposed components relative to main straight
    - Gust factor
    - Wind chill temperature
    - Beaufort scale
    - Impact assessment
    """
    speed = weather.wind_speed_kmh or 0
    direction = weather.wind_direction_deg or 0
    gust = weather.wind_gust_kmh or speed
    temp = weather.temperature_c or 20

    # Get straight bearing for this circuit
    straight_bearing = CIRCUIT_STRAIGHT_BEARINGS.get(circuit_name, 0)

    # Decompose wind
    components = decompose_wind(speed, direction, straight_bearing)

    # Gust factor (ratio of gust to sustained wind)
    gust_factor = round(gust / max(speed, 1), 2)

    # Wind chill (simplified formula)
    wind_chill = _calculate_wind_chill(temp, speed)

    # Beaufort scale
    beaufort = _beaufort_scale(speed)

    # Impact assessment
    impact = _assess_wind_impact(speed, gust, abs(components["crosswind_kmh"]))

    # Direction label
    direction_label = _direction_label(direction)

    return {
        "speed_kmh": round(speed, 1),
        "gust_kmh": round(gust, 1),
        "direction_deg": round(direction, 0),
        "direction_label": direction_label,
        "gust_factor": gust_factor,
        "beaufort_scale": beaufort["number"],
        "beaufort_description": beaufort["description"],
        "wind_chill_c": wind_chill,
        "headwind_kmh": components["headwind_kmh"],
        "crosswind_kmh": components["crosswind_kmh"],
        "crosswind_direction": components["crosswind_direction"],
        "straight_bearing": straight_bearing,
        "impact_level": impact["level"],
        "impact_details": impact["details"],
    }


def forecast_wind_analysis(
    forecast: List[ForecastData],
    circuit_name: str,
    track_conditions: Optional[List[Dict]] = None,
) -> List[Dict[str, object]]:
    """Analyze wind for each forecast point, including precipitation overlay data."""
    straight_bearing = CIRCUIT_STRAIGHT_BEARINGS.get(circuit_name, 0)
    results = []

    for i, point in enumerate(forecast[:24]):
        speed = point.wind_speed_kmh or 0
        direction = point.wind_direction_deg or 0
        gust = point.wind_gust_kmh or speed

        components = decompose_wind(speed, direction, straight_bearing)

        # Include precipitation data for map overlay
        precip_intensity = point.precipitation_intensity or 0
        precip_prob = point.precipitation_probability or 0
        cloud_cover = point.cloud_cover_pct

        # Get track condition from pre-computed conditions if available
        condition = "dry"
        if track_conditions and i < len(track_conditions):
            condition = track_conditions[i].get("condition", "dry")

        results.append({
            "forecast_time": point.forecast_time.isoformat(),
            "speed_kmh": round(speed, 1),
            "gust_kmh": round(gust, 1),
            "direction_deg": round(direction, 0),
            "direction_label": _direction_label(direction),
            "headwind_kmh": components["headwind_kmh"],
            "crosswind_kmh": components["crosswind_kmh"],
            "crosswind_direction": components["crosswind_direction"],
            "precipitation_intensity": round(precip_intensity, 2),
            "precipitation_probability": round(precip_prob, 0),
            "cloud_cover_pct": round(cloud_cover, 0) if cloud_cover is not None else None,
            "track_condition": condition,
        })

    return results


def _calculate_wind_chill(temp_c: float, wind_kmh: float) -> float:
    """Calculate wind chill temperature (Environment Canada formula)."""
    if temp_c > 10 or wind_kmh < 4.8:
        return round(temp_c, 1)
    wc = 13.12 + 0.6215 * temp_c - 11.37 * (wind_kmh ** 0.16) + 0.3965 * temp_c * (wind_kmh ** 0.16)
    return round(wc, 1)


def _beaufort_scale(speed_kmh: float) -> Dict[str, object]:
    """Convert wind speed to Beaufort scale."""
    scales = [
        (1, 0, "Calm"), (5, 1, "Light air"), (11, 2, "Light breeze"),
        (19, 3, "Gentle breeze"), (28, 4, "Moderate breeze"),
        (38, 5, "Fresh breeze"), (49, 6, "Strong breeze"),
        (61, 7, "High wind"), (74, 8, "Gale"),
        (88, 9, "Strong gale"), (102, 10, "Storm"),
        (117, 11, "Violent storm"), (999, 12, "Hurricane"),
    ]
    for threshold, number, desc in scales:
        if speed_kmh < threshold:
            return {"number": number, "description": desc}
    return {"number": 12, "description": "Hurricane"}


def _direction_label(deg: float) -> str:
    """Convert degrees to compass direction."""
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                   "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    idx = round(deg / 22.5) % 16
    return directions[idx]


def _assess_wind_impact(speed: float, gust: float, crosswind: float) -> Dict[str, object]:
    """Assess wind impact on racing."""
    details = []

    if gust > 80:
        level = "critical"
        details.append("Dangerous gusts — session may need suspension")
    elif gust > 60 or speed > 50:
        level = "high"
        details.append("Strong winds affecting car balance significantly")
    elif gust > 40 or speed > 30:
        level = "moderate"
        details.append("Noticeable wind — setup adjustments recommended")
    elif speed > 15:
        level = "low"
        details.append("Light wind — minimal impact on performance")
    else:
        level = "none"
        details.append("Calm conditions")

    if crosswind > 40:
        details.append("Severe crosswind on main straight — high-speed stability risk")
    elif crosswind > 25:
        details.append("Significant crosswind — affects braking zones and corner entry")
    elif crosswind > 15:
        details.append("Moderate crosswind — drivers should compensate")

    if gust / max(speed, 1) > 1.8:
        details.append("Gusty conditions — inconsistent aerodynamic loads")

    return {"level": level, "details": details}


def compute_wind_veer(forecast: "List[ForecastData]") -> dict:
    """Compute wind veer/backing trend over the first 24 forecast hours.

    Veering = clockwise direction shift (e.g., S→W→N) — indicates dry air advection.
    Backing = counter-clockwise shift (e.g., N→W→S) — indicates moist/unstable air.
    Uses circular angular differences to handle the 0°/360° wrap-around correctly.
    """
    dirs = [p.wind_direction_deg or 0.0 for p in forecast[:24]]
    if len(dirs) < 2:
        return {"veer_trend": "steady", "veer_rotation_deg": 0.0, "veer_meaning": "Insufficient data"}

    total_rotation = 0.0
    for i in range(1, len(dirs)):
        diff = (dirs[i] - dirs[i - 1] + 180) % 360 - 180
        total_rotation += diff

    if total_rotation > 15:
        trend = "veering"
        meaning = "Clockwise rotation — dry air advection, improving conditions"
    elif total_rotation < -15:
        trend = "backing"
        meaning = "Counter-clockwise rotation — moist/unstable air approaching"
    else:
        trend = "steady"
        meaning = "Wind direction stable over 24 h"

    return {
        "veer_trend": trend,
        "veer_rotation_deg": round(total_rotation, 1),
        "veer_meaning": meaning,
    }
