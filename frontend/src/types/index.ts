export interface Circuit {
  id: string;
  name: string;
  country: string;
  latitude: number;
  longitude: number;
  length_km: number | null;
  timezone: string | null;
  altitude_m: number | null;
  series: string | null;
  sector_count: number;
  surface_type: string | null;
}

export interface WeatherCurrent {
  circuit_id: string;
  observed_at: string;
  temperature_c: number | null;
  humidity_pct: number | null;
  wind_speed_kmh: number | null;
  wind_direction_deg: number | null;
  wind_gust_kmh: number | null;
  precipitation_intensity: number | null;
  precipitation_probability: number | null;
  cloud_cover_pct: number | null;
  visibility_km: number | null;
  pressure_hpa: number | null;
  uv_index: number | null;
  dew_point_c: number | null;
  weather_code: number | null;
  track_temperature_c: number | null;
  rain_eta_minutes: number | null;
}

export interface WeatherForecastPoint {
  forecast_time: string;
  temperature_c: number | null;
  humidity_pct: number | null;
  wind_speed_kmh: number | null;
  wind_direction_deg: number | null;
  precipitation_probability: number | null;
  precipitation_intensity: number | null;
  cloud_cover_pct: number | null;
  weather_code: number | null;
  track_temperature_c: number | null;
}

export interface Alert {
  id: string;
  alert_type: string;
  severity: "info" | "warning" | "critical";
  message: string;
  created_at: string;
  is_active: boolean;
}

export interface WindAnalysis {
  speed_kmh: number;
  gust_kmh: number;
  direction_deg: number;
  direction_label: string;
  gust_factor: number;
  beaufort_scale: number;
  beaufort_description: string;
  wind_chill_c: number;
  headwind_kmh: number;
  crosswind_kmh: number;
  crosswind_direction: string;
  straight_bearing: number;
  impact_level: string;
  impact_details: string[];
}

export interface TrackConditionPoint {
  hour: number;
  forecast_time: string;
  condition: string;
  precipitation_intensity: number;
  accumulated_rain_mm: number;
}

export interface DryingEstimate {
  condition: string;
  water_depth_mm: number;
  drying_rate_mm_hr: number;
  damp_minutes: number;
  dry_minutes: number;
}

export interface StrategyPoint {
  hour: number;
  forecast_time: string;
  track_temp_c: number;
  condition: string;
  compound: string;
  compound_alternative: string | null;
  compound_reason: string;
  rain_probability: number;
  pit_recommendation: string | null;
}

export interface GripEstimate {
  grip_pct: number;
  mechanical_grip_pct: number;
  aero_efficiency_pct: number;
  factors: Record<string, string>;
}

export interface WindForecastPoint {
  forecast_time: string;
  speed_kmh: number;
  gust_kmh: number;
  direction_deg: number;
  direction_label: string;
  headwind_kmh: number;
  crosswind_kmh: number;
  crosswind_direction: string;
  precipitation_intensity: number;
  precipitation_probability: number;
  cloud_cover_pct: number | null;
  track_condition: string;
}

export interface CircuitCorner {
  name: string;
  bearing: number;
  lat: number;
  lng: number;
}

export interface UserSession {
  id: string;
  name: string;
  startTime: string;
  endTime?: string;
  circuitId: string;
}

export interface TimeRange {
  startMs: number;
  endMs: number;
}

export type ZoomLevel = "6h" | "12h" | "24h";

export interface WeatherResponse {
  circuit_id: string;
  circuit_name: string;
  surface_type: string | null;
  confidence_pct: number;
  current: WeatherCurrent | null;
  forecast: WeatherForecastPoint[];
  alerts: Alert[];
  wind_analysis: WindAnalysis | null;
  track_conditions: TrackConditionPoint[];
  drying_estimate: DryingEstimate | null;
  strategy_timeline: StrategyPoint[];
  grip: GripEstimate | null;
  wind_forecast: WindForecastPoint[];
  circuit_corners: CircuitCorner[];
}
