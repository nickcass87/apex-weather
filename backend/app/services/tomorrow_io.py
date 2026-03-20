"""Tomorrow.io weather provider implementation."""
from __future__ import annotations

import httpx
from datetime import datetime, timezone
from typing import Optional, List

from app.core.config import settings
from app.services.weather_provider import WeatherProvider, WeatherData, ForecastData


class TomorrowIOProvider(WeatherProvider):
    """Fetches weather data from Tomorrow.io v4 API."""

    def __init__(self):
        self.api_key = settings.TOMORROW_API_KEY
        self.realtime_url = settings.TOMORROW_REALTIME_URL
        self.forecast_url = settings.TOMORROW_FORECAST_URL

    async def get_realtime(self, lat: float, lon: float) -> WeatherData:
        params = {
            "location": f"{lat},{lon}",
            "apikey": self.api_key,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self.realtime_url, params=params)
            resp.raise_for_status()
            data = resp.json()

        values = data.get("data", {}).get("values", {})
        obs_time = data.get("data", {}).get("time", datetime.now(timezone.utc).isoformat())

        return WeatherData(
            observed_at=datetime.fromisoformat(obs_time.replace("Z", "+00:00")),
            temperature_c=values.get("temperature"),
            humidity_pct=values.get("humidity"),
            wind_speed_kmh=self._ms_to_kmh(values.get("windSpeed")),
            wind_direction_deg=values.get("windDirection"),
            wind_gust_kmh=self._ms_to_kmh(values.get("windGust")),
            precipitation_intensity=values.get("rainIntensity") or values.get("precipitationIntensity") or 0,
            precipitation_probability=values.get("precipitationProbability"),
            cloud_cover_pct=values.get("cloudCover"),
            visibility_km=values.get("visibility"),
            pressure_hpa=values.get("pressureSurfaceLevel"),
            uv_index=values.get("uvIndex"),
            dew_point_c=values.get("dewPoint"),
            weather_code=values.get("weatherCode"),
        )

    async def get_forecast(self, lat: float, lon: float, hours: int = 24) -> List[ForecastData]:
        params = {
            "location": f"{lat},{lon}",
            "apikey": self.api_key,
            "timesteps": "1h",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self.forecast_url, params=params)
            resp.raise_for_status()
            data = resp.json()

        timelines = data.get("timelines", {})
        hourly = timelines.get("hourly", [])

        forecasts = []
        for entry in hourly[:hours]:
            values = entry.get("values", {})
            fc_time = entry.get("time", "")
            forecasts.append(ForecastData(
                forecast_time=datetime.fromisoformat(fc_time.replace("Z", "+00:00")),
                temperature_c=values.get("temperature"),
                humidity_pct=values.get("humidity"),
                wind_speed_kmh=self._ms_to_kmh(values.get("windSpeed")),
                wind_direction_deg=values.get("windDirection"),
                wind_gust_kmh=self._ms_to_kmh(values.get("windGust")),
                precipitation_probability=values.get("precipitationProbability"),
                precipitation_intensity=values.get("rainIntensity") or values.get("precipitationIntensity") or 0,
                cloud_cover_pct=values.get("cloudCover"),
                weather_code=values.get("weatherCode"),
            ))
        return forecasts

    @staticmethod
    def _ms_to_kmh(val: Optional[float]) -> Optional[float]:
        if val is None:
            return None
        return round(val * 3.6, 1)
