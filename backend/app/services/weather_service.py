"""High-level weather service that orchestrates providers and algorithms."""
from __future__ import annotations

import random
import math
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple

from app.core.config import settings
from app.services.weather_provider import WeatherProvider, WeatherData, ForecastData
from app.services.tomorrow_io import TomorrowIOProvider
from app.algorithms.track_temperature import estimate_track_temperature
from app.algorithms.rain_eta import estimate_rain_eta
from app.algorithms.alerts import generate_alerts

logger = logging.getLogger(__name__)

# In-memory TTL cache: key -> (timestamp, current_data, forecast_data)
_cache: dict[str, Tuple[float, WeatherData, List[ForecastData]]] = {}
CACHE_TTL_SECONDS = 600  # 10 minutes


def _cache_key(lat: float, lon: float) -> str:
    return f"{lat:.4f},{lon:.4f}"


def cache_stats() -> dict:
    """Return cache size and entry details for health endpoint."""
    now = time.time()
    return {
        "entries": len(_cache),
        "keys": [
            {"key": k, "age_seconds": round(now - v[0])}
            for k, v in _cache.items()
        ],
    }


class WeatherService:
    """Orchestrates weather data fetching and processing."""

    def __init__(self):
        self._provider: WeatherProvider = TomorrowIOProvider()
        self._demo_mode = not settings.TOMORROW_API_KEY or settings.TOMORROW_API_KEY == "your_tomorrow_io_api_key_here"

    @property
    def is_demo_mode(self) -> bool:
        return self._demo_mode

    async def _get_cached_or_fetch(
        self, lat: float, lon: float, hours: int = 24
    ) -> Tuple[WeatherData, List[ForecastData]]:
        """Return cached weather data or fetch fresh from provider."""
        key = _cache_key(lat, lon)
        now = time.time()

        if key in _cache:
            ts, current, forecast = _cache[key]
            if now - ts < CACHE_TTL_SECONDS:
                logger.debug("Cache hit for %s (age %.0fs)", key, now - ts)
                return current, forecast
            else:
                logger.debug("Cache expired for %s", key)

        current = await self._provider.get_realtime(lat, lon)
        forecast = await self._provider.get_forecast(lat, lon, hours)
        _cache[key] = (now, current, forecast)
        logger.info("Cached weather for %s", key)
        return current, forecast

    async def get_current_weather(self, lat: float, lon: float) -> WeatherData:
        if self._demo_mode:
            return self._generate_demo_current(lat, lon)
        current, _ = await self._get_cached_or_fetch(lat, lon)
        return current

    async def get_forecast(self, lat: float, lon: float, hours: int = 24) -> List[ForecastData]:
        if self._demo_mode:
            return self._generate_demo_forecast(lat, lon, hours)
        _, forecast = await self._get_cached_or_fetch(lat, lon, hours)
        return forecast

    def compute_track_temperature(self, weather: WeatherData, surface_type: str = "standard_asphalt") -> Optional[float]:
        if weather.temperature_c is None:
            return None
        solar_radiation = self._estimate_solar_radiation(weather)
        return estimate_track_temperature(
            air_temp_c=weather.temperature_c,
            solar_radiation_wm2=solar_radiation,
            wind_speed_kmh=weather.wind_speed_kmh or 0,
            cloud_cover_pct=weather.cloud_cover_pct or 0,
            humidity_pct=weather.humidity_pct or 50,
            surface_type=surface_type,
        )

    def compute_rain_eta(self, forecast: List[ForecastData], current: Optional[WeatherData] = None) -> Optional[float]:
        return estimate_rain_eta(forecast, current)

    def compute_alerts(self, weather: WeatherData, forecast: List[ForecastData]) -> List[dict]:
        return generate_alerts(weather, forecast)

    @staticmethod
    def _estimate_solar_radiation(weather: WeatherData) -> float:
        """Rough solar radiation estimate from cloud cover and UV index."""
        base = 800.0
        cloud_factor = 1.0 - ((weather.cloud_cover_pct or 0) / 100.0) * 0.7
        uv_factor = min((weather.uv_index or 0) / 10.0, 1.0)
        return base * cloud_factor * uv_factor

    @staticmethod
    def _generate_demo_current(lat: float, lon: float) -> WeatherData:
        """Generate realistic demo weather based on latitude."""
        rng = random.Random(int(abs(lat * 100 + lon * 100)) % 10000)
        base_temp = 30 - abs(lat) * 0.4 + rng.gauss(0, 2)
        wind_speed = rng.uniform(5, 22)
        wind_dir = rng.uniform(0, 360)
        return WeatherData(
            observed_at=datetime.now(timezone.utc),
            temperature_c=round(base_temp, 1),
            humidity_pct=round(rng.uniform(40, 70), 0),
            wind_speed_kmh=round(wind_speed, 1),
            wind_direction_deg=round(wind_dir, 0),
            wind_gust_kmh=round(wind_speed * rng.uniform(1.15, 1.45), 1),
            precipitation_intensity=0.0,
            precipitation_probability=round(rng.uniform(0, 20), 0),
            cloud_cover_pct=round(rng.uniform(15, 60), 0),
            visibility_km=round(rng.uniform(12, 25), 1),
            pressure_hpa=round(rng.uniform(1010, 1022), 1),
            uv_index=round(rng.uniform(2, 7), 0),
            dew_point_c=round(base_temp - rng.uniform(6, 14), 1),
            weather_code=1000,
        )

    @staticmethod
    def _generate_demo_forecast(lat: float, lon: float, hours: int) -> List[ForecastData]:
        """Generate demo hourly forecast with smooth, physically-plausible patterns.

        Uses a random walk for wind direction/speed so adjacent hours are correlated,
        and groups precipitation into a single realistic weather event rather than
        scattering random rain probabilities each hour.
        """
        rng = random.Random(int(abs(lat * 100 + lon * 100)) % 10000 + 1)
        base_temp = 30 - abs(lat) * 0.4
        now = datetime.now(timezone.utc)

        # Persistent wind state — random walk, not independent per hour
        wind_dir = rng.uniform(0, 360)
        wind_speed = rng.uniform(8, 20)

        # One optional rain event spanning 2–6 contiguous hours
        has_rain = rng.random() < 0.35
        rain_start_h = rng.randint(4, 16) if has_rain else hours + 1
        rain_duration_h = rng.randint(2, 6) if has_rain else 0
        rain_peak_mm = rng.uniform(1.0, 4.5) if has_rain else 0.0

        # Base cloud and humidity that drift slowly
        base_cloud = rng.uniform(15, 50)
        base_humidity = rng.uniform(45, 62)

        forecasts = []
        for h in range(hours):
            hour_offset = (now.hour + h) % 24

            # Temperature: smooth diurnal cycle + tiny noise
            diurnal = math.sin((hour_offset - 6) * math.pi / 12) * 4
            temp = base_temp + diurnal + rng.gauss(0, 0.4)

            # Wind direction: smooth random walk ±8° per hour
            wind_dir = (wind_dir + rng.gauss(0, 8)) % 360
            # Wind speed: diurnal pattern (calmer at night, peaks ~14:00) + mean reversion
            speed_diurnal = 1.0 + 0.3 * max(0, math.sin((hour_offset - 9) * math.pi / 12))
            target_speed = wind_speed * speed_diurnal
            wind_speed = max(2.0, wind_speed * 0.8 + target_speed * 0.2 + rng.gauss(0, 1.0))
            gust = wind_speed * rng.uniform(1.15, 1.45)

            # Rain event: smooth bell-curve intensity within the event window
            in_rain = rain_start_h <= h < rain_start_h + rain_duration_h
            if in_rain:
                progress = (h - rain_start_h) / max(1, rain_duration_h - 1)
                envelope = math.sin(progress * math.pi)
                precip_intensity = max(0.0, rain_peak_mm * envelope * rng.uniform(0.85, 1.15))
                rain_prob = min(90.0, 50 + 40 * envelope)
            else:
                precip_intensity = 0.0
                rain_prob = max(0.0, rng.uniform(-5, 12))

            # Cloud and humidity: elevated during rain, otherwise slow drift
            cloud = min(95.0, base_cloud + rng.gauss(0, 4) + (40 if in_rain else 0))
            humidity = min(95.0, base_humidity + rng.gauss(0, 2) + (22 if in_rain else 0))

            forecasts.append(ForecastData(
                forecast_time=now + timedelta(hours=h),
                temperature_c=round(temp, 1),
                humidity_pct=round(max(20.0, humidity), 0),
                wind_speed_kmh=round(wind_speed, 1),
                wind_direction_deg=round(wind_dir, 0),
                wind_gust_kmh=round(gust, 1),
                precipitation_probability=round(max(0.0, rain_prob), 0),
                precipitation_intensity=round(precip_intensity, 2) if rain_prob > 20 else 0,
                cloud_cover_pct=round(max(5.0, min(100.0, cloud)), 0),
                weather_code=4001 if in_rain else 1000,
            ))
        return forecasts
