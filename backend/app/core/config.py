from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Apex Weather"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "sqlite:///./apex_weather.db"
    TOMORROW_API_KEY: str = ""
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"

    # Tomorrow.io endpoints
    TOMORROW_REALTIME_URL: str = "https://api.tomorrow.io/v4/weather/realtime"
    TOMORROW_FORECAST_URL: str = "https://api.tomorrow.io/v4/weather/forecast"

    # Weather polling interval in seconds
    WEATHER_POLL_INTERVAL: int = 300

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
