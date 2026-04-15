from __future__ import annotations

from typing import Optional, List, Dict

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class WeatherCurrent(BaseModel):
    circuit_id: UUID
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
    provider: str = "tomorrow.io"

    # Computed fields added by the API
    track_temperature_c: Optional[float] = None
    rain_eta_minutes: Optional[float] = None
    wet_bulb_c: Optional[float] = None
    dew_point_spread_c: Optional[float] = None
    pressure_trend: Optional[str] = None  # "rising", "falling", "steady"
    pressure_trend_hpa_3h: Optional[float] = None

    model_config = {"from_attributes": True}


class WeatherForecastPoint(BaseModel):
    forecast_time: datetime
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    precipitation_probability: Optional[float] = None
    precipitation_intensity: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    weather_code: Optional[int] = None
    track_temperature_c: Optional[float] = None
    dew_point_c: Optional[float] = None
    wind_gust_kmh: Optional[float] = None
    pressure_hpa: Optional[float] = None
    solar_ghi_wm2: Optional[float] = None
    precip_type: Optional[int] = None

    model_config = {"from_attributes": True}


class WindAnalysis(BaseModel):
    speed_kmh: float = 0
    gust_kmh: float = 0
    direction_deg: float = 0
    direction_label: str = "N"
    gust_factor: float = 1.0
    beaufort_scale: int = 0
    beaufort_description: str = "Calm"
    wind_chill_c: float = 0
    headwind_kmh: float = 0
    crosswind_kmh: float = 0
    crosswind_direction: str = "left"
    straight_bearing: float = 0
    impact_level: str = "none"
    impact_details: List[str] = []
    veer_trend: str = "steady"
    veer_rotation_deg: float = 0.0
    veer_meaning: str = ""


class TrackConditionPoint(BaseModel):
    hour: int = 0
    forecast_time: datetime
    condition: str = "dry"
    precipitation_intensity: float = 0
    accumulated_rain_mm: float = 0


class DryingEstimate(BaseModel):
    condition: str = "dry"
    water_depth_mm: float = 0
    drying_rate_mm_hr: float = 0
    damp_minutes: float = 0
    dry_minutes: float = 0
    temp_factor: Optional[float] = None
    wind_factor: Optional[float] = None
    humidity_factor: Optional[float] = None
    solar_factor: Optional[float] = None
    drain_factor: Optional[float] = None


class StrategyPoint(BaseModel):
    hour: int = 0
    forecast_time: datetime
    track_temp_c: float = 0
    condition: str = "dry"
    compound: str = "medium"
    compound_alternative: Optional[str] = None
    compound_reason: str = ""
    rain_probability: float = 0
    pit_recommendation: Optional[str] = None


class GripEstimate(BaseModel):
    grip_pct: float = 85
    mechanical_grip_pct: float = 85
    aero_efficiency_pct: float = 100
    factors: Dict[str, str] = {}


class WindForecastPoint(BaseModel):
    forecast_time: datetime
    speed_kmh: float = 0
    gust_kmh: float = 0
    direction_deg: float = 0
    direction_label: str = "N"
    headwind_kmh: float = 0
    crosswind_kmh: float = 0
    crosswind_direction: str = "left"
    # Precipitation overlay data
    precipitation_intensity: float = 0
    precipitation_probability: float = 0
    cloud_cover_pct: Optional[float] = None
    track_condition: str = "dry"


class CircuitCorner(BaseModel):
    name: str
    bearing: float
    lat: float
    lng: float


class WeatherResponse(BaseModel):
    circuit_id: UUID
    circuit_name: str
    surface_type: Optional[str] = None
    confidence_pct: int = 100
    current: Optional[WeatherCurrent] = None
    forecast: List[WeatherForecastPoint] = []
    alerts: List["AlertOut"] = []
    # New fields
    wind_analysis: Optional[WindAnalysis] = None
    track_conditions: List[TrackConditionPoint] = []
    drying_estimate: Optional[DryingEstimate] = None
    strategy_timeline: List[StrategyPoint] = []
    grip: Optional[GripEstimate] = None
    wind_forecast: List[WindForecastPoint] = []
    circuit_corners: List[CircuitCorner] = []
    nowcast: Optional["NowcastResponse"] = None


class AlertOut(BaseModel):
    id: UUID
    alert_type: str
    severity: str
    message: str
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class NowcastPoint(BaseModel):
    forecast_time: datetime
    temperature_c: Optional[float] = None
    precipitation_intensity: Optional[float] = None
    precipitation_probability: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    precip_type: Optional[int] = None


class NowcastResponse(BaseModel):
    circuit_id: str
    circuit_name: str
    fetched_at: datetime
    points: List[NowcastPoint] = []
    has_rain_60min: bool = False
    peak_intensity_mmhr: float = 0.0
    rain_onset_minutes: Optional[int] = None


# Resolve forward reference
WeatherResponse.model_rebuild()


# ── Multi-model comparison schemas ──

class ModelForecastPoint(BaseModel):
    time: str
    temp_c: float = 0
    precip_mm: float = 0
    wind_kmh: float = 0
    wind_dir: float = 0
    cloud_pct: float = 0


class ModelComparison(BaseModel):
    model_id: str
    label: str
    provider: str
    color: str
    points: List[ModelForecastPoint] = []


class ModelComparisonResponse(BaseModel):
    fetched_at: str
    models: List[ModelComparison] = []
