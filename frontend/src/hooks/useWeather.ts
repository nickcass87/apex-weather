"use client";

import { useState, useEffect, useCallback } from "react";
import { WeatherResponse, ModelComparisonResponse } from "@/types";
import { getWeather, getModelComparison } from "@/lib/api";

export function useWeather(circuitId: string | null) {
  const [weather, setWeather] = useState<WeatherResponse | null>(null);
  const [modelComparison, setModelComparison] = useState<ModelComparisonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchWeather = useCallback(async () => {
    if (!circuitId) return;
    setLoading(true);
    setError(null);
    try {
      // Fetch weather + model comparison in parallel
      const [weatherData, modelsData] = await Promise.all([
        getWeather(circuitId),
        getModelComparison(circuitId).catch(() => null), // Non-critical — fail silently
      ]);
      setWeather(weatherData);
      if (modelsData) setModelComparison(modelsData);
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

  return { weather, modelComparison, loading, error, refetch: fetchWeather };
}
