"""Data export API for weather reports.

Provides CSV and JSON export of weather data for offline analysis.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.circuit import Circuit
from app.services.weather_service import WeatherService
from app.algorithms.track_temperature import estimate_track_temp_from_forecast

router = APIRouter(prefix="/export", tags=["export"])

weather_service = WeatherService()


@router.get("/forecast/{circuit_id}/csv")
async def export_forecast_csv(circuit_id: str, db: Session = Depends(get_db)):
    """Export 24h forecast as CSV."""
    circuit = db.query(Circuit).filter(Circuit.id == circuit_id).first()
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")

    surface = circuit.surface_type or "standard_asphalt"

    try:
        forecast_data = await weather_service.get_forecast(circuit.latitude, circuit.longitude, hours=24)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather error: {str(e)}")

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "forecast_time", "temperature_c", "track_temp_c", "humidity_pct",
        "wind_speed_kmh", "wind_direction_deg", "precipitation_probability",
        "precipitation_intensity_mm_hr", "cloud_cover_pct", "weather_code",
    ])

    for fp in forecast_data:
        track_temp = estimate_track_temp_from_forecast(
            air_temp_c=fp.temperature_c or 20,
            wind_speed_kmh=fp.wind_speed_kmh or 0,
            cloud_cover_pct=fp.cloud_cover_pct or 0,
            humidity_pct=fp.humidity_pct or 50,
            surface_type=surface,
        )
        writer.writerow([
            fp.forecast_time.isoformat(),
            fp.temperature_c,
            round(track_temp, 1),
            fp.humidity_pct,
            fp.wind_speed_kmh,
            fp.wind_direction_deg,
            fp.precipitation_probability,
            fp.precipitation_intensity,
            fp.cloud_cover_pct,
            fp.weather_code,
        ])

    output.seek(0)
    filename = f"apex_weather_{circuit.name.replace(' ', '_')}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/forecast/{circuit_id}/json")
async def export_forecast_json(circuit_id: str, db: Session = Depends(get_db)):
    """Export 24h forecast as JSON with metadata."""
    circuit = db.query(Circuit).filter(Circuit.id == circuit_id).first()
    if not circuit:
        raise HTTPException(status_code=404, detail="Circuit not found")

    surface = circuit.surface_type or "standard_asphalt"

    try:
        current = await weather_service.get_current_weather(circuit.latitude, circuit.longitude)
        forecast_data = await weather_service.get_forecast(circuit.latitude, circuit.longitude, hours=24)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather error: {str(e)}")

    points = []
    for fp in forecast_data:
        track_temp = estimate_track_temp_from_forecast(
            air_temp_c=fp.temperature_c or 20,
            wind_speed_kmh=fp.wind_speed_kmh or 0,
            cloud_cover_pct=fp.cloud_cover_pct or 0,
            humidity_pct=fp.humidity_pct or 50,
            surface_type=surface,
        )
        points.append({
            "forecast_time": fp.forecast_time.isoformat(),
            "temperature_c": fp.temperature_c,
            "track_temperature_c": round(track_temp, 1),
            "humidity_pct": fp.humidity_pct,
            "wind_speed_kmh": fp.wind_speed_kmh,
            "wind_direction_deg": fp.wind_direction_deg,
            "precipitation_probability": fp.precipitation_probability,
            "precipitation_intensity_mm_hr": fp.precipitation_intensity,
            "cloud_cover_pct": fp.cloud_cover_pct,
        })

    return {
        "export_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "circuit_name": circuit.name,
            "circuit_country": circuit.country,
            "surface_type": surface,
            "coordinates": {"lat": circuit.latitude, "lon": circuit.longitude},
        },
        "current_conditions": {
            "observed_at": current.observed_at.isoformat(),
            "temperature_c": current.temperature_c,
            "humidity_pct": current.humidity_pct,
            "wind_speed_kmh": current.wind_speed_kmh,
            "precipitation_intensity": current.precipitation_intensity,
        },
        "forecast": points,
    }
