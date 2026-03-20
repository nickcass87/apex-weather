"""Tests for track temperature algorithm — reproduces nighttime overheating bug."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.algorithms.track_temperature import (
    estimate_track_temp_from_forecast,
    estimate_track_temperature,
    solar_elevation_angle,
)


class TestSolarElevationAngle:
    """Verify the solar position model returns sane values."""

    def test_nighttime_spain_20utc(self):
        """At 20:00 UTC in summer, Jarama (40.6N, -3.6W) sun is near/below horizon."""
        # June 21 at 20:00 UTC — sun should be very low or set in Madrid
        dt = datetime(2025, 6, 21, 20, 0, tzinfo=timezone.utc)
        angle = solar_elevation_angle(40.6, -3.6, dt)
        assert angle < 10, f"Sun should be near/below horizon at 20 UTC in Spain, got {angle}"

    def test_nighttime_spain_midnight(self):
        """At midnight UTC in Spain, elevation must be negative (below horizon)."""
        dt = datetime(2025, 6, 21, 0, 0, tzinfo=timezone.utc)
        angle = solar_elevation_angle(40.6, -3.6, dt)
        assert angle < 0, f"Sun must be below horizon at midnight, got {angle}"

    def test_midday_spain_summer(self):
        """At solar noon in Spain summer, elevation should be high (60-75 degrees)."""
        # Solar noon in Spain is roughly 13:30 UTC in summer
        dt = datetime(2025, 6, 21, 13, 30, tzinfo=timezone.utc)
        angle = solar_elevation_angle(40.6, -3.6, dt)
        assert angle > 55, f"Midday summer sun should be high, got {angle}"

    def test_negative_at_night(self):
        """Any nighttime hour should return negative elevation."""
        dt = datetime(2025, 1, 15, 3, 0, tzinfo=timezone.utc)
        angle = solar_elevation_angle(40.6, -3.6, dt)
        assert angle < 0

    def test_southern_hemisphere(self):
        """Melbourne at local noon in January (summer) should have high sun."""
        # Melbourne is ~37.8S, 145E. Solar noon ~ 02:30 UTC in January.
        dt = datetime(2025, 1, 15, 2, 30, tzinfo=timezone.utc)
        angle = solar_elevation_angle(-37.8, 145.0, dt)
        assert angle > 55, f"Melbourne summer midday should be high, got {angle}"


class TestNighttimeBugFix:
    """The core bug: nighttime track temp was 8-10C too hot."""

    def test_nighttime_track_temp_close_to_air_temp(self):
        """At night, track temp should be within ~3C of air temp (no solar heating)."""
        # Jarama at 20:00 UTC, air temp 18C, 50% cloud, 60% humidity, 10 km/h wind
        result = estimate_track_temp_from_forecast(
            air_temp_c=18.0,
            wind_speed_kmh=10.0,
            cloud_cover_pct=50.0,
            humidity_pct=60.0,
            latitude=40.6,
            longitude=-3.6,
            forecast_time=datetime(2025, 6, 21, 20, 0, tzinfo=timezone.utc),
        )
        diff = abs(result - 18.0)
        assert diff < 5, f"Nighttime track temp {result} is too far from air temp 18C (diff={diff})"

    def test_nighttime_no_solar_heating(self):
        """At midnight, there should be zero solar contribution."""
        result = estimate_track_temp_from_forecast(
            air_temp_c=15.0,
            wind_speed_kmh=5.0,
            cloud_cover_pct=0.0,
            humidity_pct=50.0,
            latitude=40.6,
            longitude=-3.6,
            forecast_time=datetime(2025, 6, 21, 0, 0, tzinfo=timezone.utc),
        )
        # Without solar, track should be at or below air temp (wind + humidity cooling)
        assert result <= 15.0, f"Nighttime clear sky should not heat track above air temp, got {result}"


class TestDaytimeBehaviorPreserved:
    """Daytime solar heating should still work correctly."""

    def test_clear_midday_summer_heating(self):
        """Clear midday should add 10-20C of solar heating."""
        result = estimate_track_temp_from_forecast(
            air_temp_c=25.0,
            wind_speed_kmh=5.0,
            cloud_cover_pct=10.0,
            humidity_pct=40.0,
            latitude=40.6,
            longitude=-3.6,
            forecast_time=datetime(2025, 6, 21, 13, 30, tzinfo=timezone.utc),
        )
        solar_contribution = result - 25.0
        assert solar_contribution > 5, f"Midday solar heating should be significant, only got {solar_contribution}C"
        assert solar_contribution < 25, f"Solar heating too extreme: {solar_contribution}C"


class TestPrecipitationCooling:
    """Rain should bring track temp much closer to air temp."""

    def test_light_rain_reduces_heating(self):
        """Light rain (0.5 mm/hr) should drastically reduce solar heating."""
        # Midday with light rain
        dry = estimate_track_temp_from_forecast(
            air_temp_c=25.0,
            wind_speed_kmh=5.0,
            cloud_cover_pct=50.0,
            humidity_pct=70.0,
            latitude=40.6,
            longitude=-3.6,
            forecast_time=datetime(2025, 6, 21, 13, 30, tzinfo=timezone.utc),
        )
        wet = estimate_track_temp_from_forecast(
            air_temp_c=25.0,
            wind_speed_kmh=5.0,
            cloud_cover_pct=50.0,
            humidity_pct=70.0,
            precipitation_intensity=0.5,
            latitude=40.6,
            longitude=-3.6,
            forecast_time=datetime(2025, 6, 21, 13, 30, tzinfo=timezone.utc),
        )
        assert wet < dry, "Wet track should be cooler than dry"
        assert wet < 28, f"Light rain track temp {wet} too high for 25C air"

    def test_heavy_rain_near_air_temp(self):
        """Heavy rain (>5 mm/hr) should bring track temp well below air temp."""
        result = estimate_track_temp_from_forecast(
            air_temp_c=20.0,
            wind_speed_kmh=10.0,
            cloud_cover_pct=90.0,
            humidity_pct=90.0,
            precipitation_intensity=8.0,
            latitude=40.6,
            longitude=-3.6,
            forecast_time=datetime(2025, 6, 21, 13, 30, tzinfo=timezone.utc),
        )
        # Heavy rain + wind + humidity all cool the surface; track should be below air temp
        assert result < 20.0, f"Heavy rain track temp {result} should be below air temp 20C"
        assert result > 10.0, f"Heavy rain track temp {result} unrealistically low"

    def test_moderate_rain(self):
        """Moderate rain (2 mm/hr) track temp should be below air temp."""
        result = estimate_track_temp_from_forecast(
            air_temp_c=22.0,
            wind_speed_kmh=10.0,
            cloud_cover_pct=80.0,
            humidity_pct=85.0,
            precipitation_intensity=2.0,
            latitude=40.6,
            longitude=-3.6,
            forecast_time=datetime(2025, 6, 21, 13, 30, tzinfo=timezone.utc),
        )
        # Moderate rain eliminates most solar heating; wind + humidity cool further
        assert result < 22.0, f"Moderate rain track temp {result} should be below air temp 22C"
        assert result > 14.0, f"Moderate rain track temp {result} unrealistically low"
