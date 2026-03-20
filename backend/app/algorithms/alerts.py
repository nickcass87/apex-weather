"""Weather alerts engine.

Generates alerts based on current conditions and forecast data.
Alert types: rain, wind, temperature, grip.
Severity levels: info, warning, critical.
"""
from __future__ import annotations

from typing import Optional, List

from app.services.weather_provider import WeatherData, ForecastData


def generate_alerts(weather: WeatherData, forecast: List[ForecastData]) -> List[dict]:
    """Generate a list of weather alerts based on current and forecast conditions."""
    alerts = []

    # Rain alerts
    rain_alert = _check_rain(weather, forecast)
    if rain_alert:
        alerts.append(rain_alert)

    # Wind alerts
    wind_alert = _check_wind(weather)
    if wind_alert:
        alerts.append(wind_alert)

    # Temperature drop alert
    temp_alert = _check_temperature_drop(weather, forecast)
    if temp_alert:
        alerts.append(temp_alert)

    # Low grip conditions
    grip_alert = _check_grip(weather)
    if grip_alert:
        alerts.append(grip_alert)

    return alerts


def _check_rain(weather: WeatherData, forecast: List[ForecastData]) -> Optional[dict]:
    # Currently raining
    if (weather.precipitation_intensity or 0) > 0.5:
        return {
            "alert_type": "rain",
            "severity": "critical",
            "message": f"Active rainfall detected: {weather.precipitation_intensity:.1f} mm/hr",
        }

    # Rain in forecast
    for i, point in enumerate(forecast[:6]):  # Next 6 hours
        prob = point.precipitation_probability or 0
        if prob >= 70:
            return {
                "alert_type": "rain",
                "severity": "warning",
                "message": f"Rain likely within {i + 1}h ({prob:.0f}% probability)",
            }
        elif prob >= 40:
            return {
                "alert_type": "rain",
                "severity": "info",
                "message": f"Rain possible within {i + 1}h ({prob:.0f}% probability)",
            }

    return None


def _check_wind(weather: WeatherData) -> Optional[dict]:
    speed = weather.wind_speed_kmh or 0
    gust = weather.wind_gust_kmh or 0

    if gust > 80 or speed > 60:
        return {
            "alert_type": "wind",
            "severity": "critical",
            "message": f"Dangerous wind: {speed:.0f} km/h, gusts {gust:.0f} km/h",
        }
    elif gust > 50 or speed > 40:
        return {
            "alert_type": "wind",
            "severity": "warning",
            "message": f"Strong wind: {speed:.0f} km/h, gusts {gust:.0f} km/h",
        }
    return None


def _check_temperature_drop(weather: WeatherData, forecast: List[ForecastData]) -> Optional[dict]:
    if not forecast or weather.temperature_c is None:
        return None

    current_temp = weather.temperature_c
    for point in forecast[:3]:  # Next 3 hours
        if point.temperature_c is not None:
            drop = current_temp - point.temperature_c
            if drop >= 5:
                return {
                    "alert_type": "temperature",
                    "severity": "warning",
                    "message": f"Temperature dropping: {drop:.1f}°C decrease expected",
                }
    return None


def _check_grip(weather: WeatherData) -> Optional[dict]:
    """Low grip warning based on humidity + precipitation."""
    humidity = weather.humidity_pct or 0
    precip = weather.precipitation_intensity or 0
    temp = weather.temperature_c or 20

    if precip > 0.1 and temp < 10:
        return {
            "alert_type": "grip",
            "severity": "critical",
            "message": "Very low grip: cold + wet conditions",
        }
    elif humidity > 90 and precip > 0:
        return {
            "alert_type": "grip",
            "severity": "warning",
            "message": "Reduced grip: high humidity with precipitation",
        }
    return None
