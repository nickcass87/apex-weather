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
      const [weatherData, nowcastData, calibrationData] = await Promise.all([
        getWeather(circuitId),
        getNowcast(circuitId).catch(() => null),
        getCalibration(circuitId).catch(() => null),
      ]);
      setWeather(weatherData);
      if (nowcastData) setNowcast(nowcastData);
      if (calibrationData) setCalibration(calibrationData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch weather");
    } finally {
      setLoading(false);
    }
  }, [circuitId]);

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
