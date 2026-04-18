"use client";

import { useState, useEffect, useCallback } from "react";
import { Circuit, WeatherResponse, ModelComparisonResponse, NowcastResponse, CalibrationStats } from "@/types";
import { getWeather, getNowcast, getCalibration } from "@/lib/api";

const OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast";

const MODELS = [
  { id: "ecmwf_ifs025", label: "ECMWF IFS", provider: "European Centre", color: "#5a9dba" },
  { id: "gfs_seamless", label: "GFS", provider: "NOAA (US)", color: "#d9af42" },
  { id: "icon_seamless", label: "ICON", provider: "DWD (Germany)", color: "#4aad7c" },
];

/** Fetch multi-model comparison directly from Open-Meteo (CORS-safe, no backend needed). */
async function fetchMultiModelDirect(latitude: number, longitude: number): Promise<ModelComparisonResponse> {
  const modelIds = MODELS.map((m) => m.id).join(",");
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
    hourly: "temperature_2m,precipitation,wind_speed_10m,wind_direction_10m,cloud_cover",
    models: modelIds,
    forecast_hours: "24",
    timezone: "UTC",
    wind_speed_unit: "kmh",
  });

  const res = await fetch(`${OPEN_METEO_URL}?${params}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Open-Meteo error: ${res.status}`);
  const data = await res.json();

  const hourly = data.hourly ?? {};
  const times: string[] = hourly.time ?? [];

  const models = MODELS.map((meta) => {
    const suffix = `_${meta.id}`;
    const temps: number[] = hourly[`temperature_2m${suffix}`] ?? [];
    const precips: number[] = hourly[`precipitation${suffix}`] ?? [];
    const winds: number[] = hourly[`wind_speed_10m${suffix}`] ?? [];
    const windDirs: number[] = hourly[`wind_direction_10m${suffix}`] ?? [];
    const clouds: number[] = hourly[`cloud_cover${suffix}`] ?? [];

    const points = times.map((time, i) => ({
      time,
      temp_c: temps[i] ?? 0,
      precip_mm: precips[i] ?? 0,
      wind_kmh: winds[i] ?? 0,
      wind_dir: windDirs[i] ?? 0,
      cloud_pct: clouds[i] ?? 0,
    }));

    return { model_id: meta.id, label: meta.label, provider: meta.provider, color: meta.color, points };
  });

  return { fetched_at: new Date().toISOString(), models };
}

/** Fetch current + forecast directly from Tomorrow.io via the Next.js server route.
 *  This bypasses the Render backend, ensuring live accurate data at all times. */
async function fetchTomorrowDirect(lat: number, lon: number): Promise<{ current: Partial<WeatherResponse["current"]>; forecast: WeatherResponse["forecast"] } | null> {
  try {
    const res = await fetch(`/api/tomorrow-current?lat=${lat}&lon=${lon}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export function useWeather(circuitId: string | null, circuit?: Circuit | null) {
  const [weather, setWeather] = useState<WeatherResponse | null>(null);
  const [modelComparison, setModelComparison] = useState<ModelComparisonResponse | null>(null);
  const [nowcast, setNowcast] = useState<NowcastResponse | null>(null);
  const [calibration, setCalibration] = useState<CalibrationStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchWeather = useCallback(async () => {
    if (!circuitId) return;
    setLoading(true);
    setError(null);
    try {
      // Fetch Render backend data (algorithms, track conditions, grip, etc.)
      // and direct Tomorrow.io data (accurate current conditions) in parallel.
      const [weatherData, tomorrowData, nowcastData, calibrationData] = await Promise.all([
        getWeather(circuitId),
        circuit?.latitude && circuit?.longitude
          ? fetchTomorrowDirect(circuit.latitude, circuit.longitude)
          : Promise.resolve(null),
        getNowcast(circuitId).catch(() => null),
        getCalibration(circuitId).catch(() => null),
      ]);

      // Override stale Render current conditions with live Tomorrow.io values.
      if (tomorrowData?.current && weatherData.current) {
        const t = tomorrowData.current as Partial<typeof weatherData.current>;
        const c = weatherData.current;
        if (t.temperature_c != null) c.temperature_c = t.temperature_c;
        if (t.humidity_pct != null) c.humidity_pct = t.humidity_pct;
        if (t.wind_speed_kmh != null) c.wind_speed_kmh = t.wind_speed_kmh;
        if (t.wind_direction_deg != null) c.wind_direction_deg = t.wind_direction_deg;
        if (t.wind_gust_kmh != null) c.wind_gust_kmh = t.wind_gust_kmh;
        // Always set precipitation from Tomorrow.io (use 0 if null — null means no rain)
        c.precipitation_intensity = t.precipitation_intensity ?? 0;
        c.precipitation_probability = t.precipitation_probability ?? 0;
        if (t.cloud_cover_pct != null) c.cloud_cover_pct = t.cloud_cover_pct;
        if (t.pressure_hpa != null) c.pressure_hpa = t.pressure_hpa;
        if (t.uv_index != null) c.uv_index = t.uv_index;
        if (t.dew_point_c != null) c.dew_point_c = t.dew_point_c;
        if (t.weather_code != null) c.weather_code = t.weather_code;
        if (t.observed_at) c.observed_at = t.observed_at as string;
        if (t.visibility_km != null) c.visibility_km = t.visibility_km;

        // Recompute rain_eta from Tomorrow.io forecast probability.
        // If Tomorrow.io shows 0% probability now, override stale Render estimate.
        if ((t.precipitation_probability ?? 0) === 0 && (t.precipitation_intensity ?? 0) === 0) {
          // Find first forecast hour with >30% probability as ETA
          const fcHours = tomorrowData.forecast ?? [];
          let etaMinutes: number | null = null;
          const now = Date.now();
          for (const fp of fcHours) {
            const prob = (fp.precipitation_probability as number) ?? 0;
            const intensity = (fp.precipitation_intensity as number) ?? 0;
            if (prob > 30 || intensity > 0.1) {
              const forecastMs = new Date(fp.forecast_time as string).getTime();
              etaMinutes = Math.max(0, (forecastMs - now) / 60000);
              break;
            }
          }
          c.rain_eta_minutes = etaMinutes;
        }
      }

      // Override ALL stale Render forecast/condition data with Tomorrow.io values.
      if (tomorrowData?.forecast?.length) {
        // Build a map of hour-index → Tomorrow.io precip/temp for fast lookup
        const tMap = new Map(tomorrowData.forecast.map((tp, i) => [i, tp]));

        // 1. weather.forecast — temperature, wind, precipitation
        weatherData.forecast?.forEach((fp, i) => {
          const tp = tMap.get(i);
          if (!tp) return;
          if (tp.temperature_c != null) fp.temperature_c = tp.temperature_c as number;
          if (tp.humidity_pct != null) fp.humidity_pct = tp.humidity_pct as number;
          if (tp.wind_speed_kmh != null) fp.wind_speed_kmh = tp.wind_speed_kmh as number;
          if (tp.wind_direction_deg != null) fp.wind_direction_deg = tp.wind_direction_deg as number;
          if (tp.cloud_cover_pct != null) fp.cloud_cover_pct = tp.cloud_cover_pct as number;
          fp.precipitation_probability = (tp.precipitation_probability as number) ?? 0;
          fp.precipitation_intensity = (tp.precipitation_intensity as number) ?? 0;
          if (fp.precipitation_intensity === 0) fp.precip_type = 0;
        });

        // 2. wind_forecast — clears DRIZZLE badge and track_condition in the wind map
        weatherData.wind_forecast?.forEach((wf, i) => {
          const tp = tMap.get(i);
          if (!tp) return;
          wf.precipitation_intensity = (tp.precipitation_intensity as number) ?? 0;
          wf.precipitation_probability = (tp.precipitation_probability as number) ?? 0;
          // Recompute track_condition: if no precip → dry
          if (wf.precipitation_intensity === 0 && wf.precipitation_probability < 20) {
            wf.track_condition = "dry";
          }
        });

        // 3. track_conditions — drives Surface Conditions panel (DAMP/WET/DRY)
        weatherData.track_conditions?.forEach((tc, i) => {
          const tp = tMap.get(i);
          if (!tp) return;
          tc.precipitation_intensity = (tp.precipitation_intensity as number) ?? 0;
          if (tc.precipitation_intensity === 0) {
            tc.accumulated_rain_mm = 0;
            tc.condition = "dry";
          }
        });

        // 4. drying_estimate — if Tomorrow.io shows no rain and no recent accumulation, clear it
        const anyRain = tomorrowData.forecast.some(
          (tp) => ((tp.precipitation_intensity as number) ?? 0) > 0.05
        );
        if (!anyRain && (tomorrowData.current?.precipitation_intensity ?? 0) === 0) {
          if (weatherData.drying_estimate) {
            weatherData.drying_estimate.condition = "dry";
            weatherData.drying_estimate.water_depth_mm = 0;
            weatherData.drying_estimate.drying_rate_mm_hr = 0;
          }
        }
      }

      setWeather(weatherData);
      if (nowcastData) setNowcast(nowcastData);
      if (calibrationData) setCalibration(calibrationData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch weather");
    } finally {
      setLoading(false);
    }
  }, [circuitId, circuit?.latitude, circuit?.longitude]);

  // Fetch model comparison directly from Open-Meteo whenever circuit changes.
  // Open-Meteo explicitly supports browser CORS — no backend proxy needed.
  const fetchModels = useCallback(async () => {
    if (!circuit?.latitude || !circuit?.longitude) return;
    try {
      const data = await fetchMultiModelDirect(circuit.latitude, circuit.longitude);
      setModelComparison(data);
    } catch {
      // Non-critical — panel hides itself when models is empty
    }
  }, [circuit?.latitude, circuit?.longitude]);

  useEffect(() => {
    fetchWeather();
    const interval = setInterval(fetchWeather, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchWeather]);

  useEffect(() => {
    fetchModels();
    const interval = setInterval(fetchModels, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchModels]);

  return { weather, modelComparison, nowcast, calibration, loading, error, refetch: fetchWeather };
}
