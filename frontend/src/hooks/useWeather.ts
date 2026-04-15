"use client";

import { useState, useEffect, useCallback } from "react";
import { WeatherResponse, ModelComparisonResponse, NowcastResponse, CalibrationStats } from "@/types";
import { getWeather, getModelComparison, getNowcast, getCalibration } from "@/lib/api";

export function useWeather(circuitId: string | null) {
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
      // Fetch weather + model comparison + nowcast + calibration in parallel
      const [weatherData, modelsData, nowcastData, calibrationData] = await Promise.all([
        getWeather(circuitId),
        getModelComparison(circuitId).catch(() => null),
        getNowcast(circuitId).catch(() => null),
        getCalibration(circuitId).catch(() => null),
      ]);
      setWeather(weatherData);
      if (modelsData) setModelComparison(modelsData);
      if (nowcastData) setNowcast(nowcastData);
      if (calibrationData) setCalibration(calibrationData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch weather");
    } finally {
      setLoading(false);
    }
  }, [circuitId]);

  useEffect(() => {
    fetchWeather();
    // Auto-refresh every 5 minutes
    const interval = setInterval(fetchWeather, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchWeather]);

  return { weather, modelComparison, nowcast, calibration, loading, error, refetch: fetchWeather };
}
