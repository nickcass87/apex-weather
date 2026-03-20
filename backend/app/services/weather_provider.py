"""Abstract weather provider interface for multi-source support."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class WeatherData:
    """Normalized weather data from any provider."""
    observed_at: datetime
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    wind_gust_kmh: Optional[float] = None
    precipitation_intensity: Optional[float] = None
    precipitation_probability: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    visibility_km: Optional[float] = None
    pressure_hpa: Optional[float] = None
    uv_index: Optional[float] = None
    dew_point_c: Optional[float] = None
    weather_code: Optional[int] = None


@dataclass
class ForecastData:
    """Normalized forecast data point."""
    forecast_time: datetime
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    wind_gust_kmh: Optional[float] = None
    precipitation_probability: Optional[float] = None
    precipitation_intensity: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    weather_code: Optional[int] = None


class WeatherProvider(ABC):
    """Base class for weather data providers."""

    @abstractmethod
    async def get_realtime(self, lat: float, lon: float) -> WeatherData:
        ...

    @abstractmethod
    async def get_forecast(self, lat: float, lon: float, hours: int = 24) -> List[ForecastData]:
        ...
