"use client";

import { useState, useEffect, useMemo } from "react";
import { Circuit, ZoomLevel, TimeRange } from "@/types";
import { getCircuits } from "@/lib/api";
import { useWeather } from "@/hooks/useWeather";
import { useLocalSessions } from "@/hooks/useLocalSessions";
import { interpolateForecast, interpolateTrackConditions } from "@/lib/interpolate";
import ApexLogo from "@/components/ApexLogo";
import CircuitSelector from "@/components/CircuitSelector";
import WeatherTiles from "@/components/WeatherTiles";
import AlertsPanel from "@/components/AlertsPanel";
import ForecastChart from "@/components/ForecastChart";
import CircuitMap from "@/components/CircuitMap";
import ConfidenceIndicator from "@/components/ConfidenceIndicator";
import TrackTempChart from "@/components/TrackTempChart";
import RainIntensityChart from "@/components/RainIntensityChart";
import ModelComparisonPanel from "@/components/ModelComparisonPanel";
import WindAnalysisPanel from "@/components/WindAnalysisPanel";
import SurfaceConditionsPanel from "@/components/SurfaceConditionsPanel";
import GripIndicator from "@/components/GripIndicator";
import SessionInput from "@/components/SessionInput";
import ExportButton from "@/components/ExportButton";
import TimeSlider from "@/components/TimeSlider";
import ChartZoomControls from "@/components/ChartZoomControls";

function formatSurfaceType(type: string): string {
  const labels: Record<string, string> = {
    standard_asphalt: "Standard Asphalt",
    high_grip_asphalt: "High-Grip Asphalt",
    abrasive: "Abrasive Surface",
    low_grip_street: "Street Circuit",
    concrete_mix: "Concrete/Asphalt Mix",
  };
  return labels[type] || type;
}

const ZOOM_MS: Record<ZoomLevel, number> = {
  "6h": 6 * 3600000,
  "12h": 12 * 3600000,
  "24h": 24 * 3600000,
};

export default function Dashboard() {
  const [circuits, setCircuits] = useState<Circuit[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [circuitsError, setCircuitsError] = useState<string | null>(null);
  const [windHourIndex, setWindHourIndex] = useState(0);
  const [zoomLevel, setZoomLevel] = useState<ZoomLevel>("24h");
  const [panOffsetMs, setPanOffsetMs] = useState(0);

  const selectedCircuit = circuits.find((c) => c.id === selectedId) || null;
  const { weather, modelComparison, loading, error, refetch } = useWeather(selectedId);
  const { sessions, addSession, removeSession } = useLocalSessions(selectedId);

  useEffect(() => {
    setWindHourIndex(0);
    setZoomLevel("24h");
    setPanOffsetMs(0);
  }, [selectedId]);

  useEffect(() => {
    getCircuits()
      .then((data) => {
        setCircuits(data);
        if (data.length > 0 && !selectedId) {
          // Default to Jarama circuit; fall back to first circuit
          const jarama = data.find((c: Circuit) => c.name.includes("Jarama"));
          setSelectedId(jarama ? jarama.id : data[0].id);
        }
      })
      .catch((err) => setCircuitsError(err.message));
  }, []);

  // Interpolate forecast to 10-min intervals
  const interpolatedForecast = useMemo(
    () => (weather ? interpolateForecast(weather.forecast) : []),
    [weather?.forecast],
  );

  const interpolatedConditions = useMemo(
    () => (weather ? interpolateTrackConditions(weather.track_conditions || []) : []),
    [weather?.track_conditions],
  );

  // Compute forecast bounds
  const forecastStartMs = useMemo(() => {
    if (!weather || weather.forecast.length === 0) return 0;
    return new Date(weather.forecast[0].forecast_time).getTime();
  }, [weather?.forecast]);

  const forecastEndMs = useMemo(() => {
    if (!weather || weather.forecast.length === 0) return 0;
    return new Date(weather.forecast[weather.forecast.length - 1].forecast_time).getTime();
  }, [weather?.forecast]);

  // Compute visible time range from zoom + pan
  const timeRange: TimeRange = useMemo(() => {
    if (forecastStartMs === 0) return { startMs: 0, endMs: 0 };
    const totalMs = forecastEndMs - forecastStartMs;
    const windowMs = Math.min(ZOOM_MS[zoomLevel], totalMs);
    const clampedPan = Math.min(panOffsetMs, Math.max(0, totalMs - windowMs));
    return {
      startMs: forecastStartMs + clampedPan,
      endMs: forecastStartMs + clampedPan + windowMs,
    };
  }, [forecastStartMs, forecastEndMs, zoomLevel, panOffsetMs]);

  return (
    <div className="min-h-screen flex flex-col">
      {/* ─── Header ─── */}
      <header
        className="sticky top-0 z-50 backdrop-blur-xl px-5 py-2"
        style={{
          background: 'linear-gradient(180deg, rgba(11,10,14,0.92) 0%, rgba(11,10,14,0.80) 100%)',
          borderBottom: '1px solid var(--border-subtle)',
          boxShadow: '0 1px 24px rgba(0,0,0,0.4)',
        }}
      >
        <div className="max-w-[1600px] mx-auto flex items-center justify-between gap-5">
          {/* Brand */}
          <div className="flex items-center gap-2">
            <ApexLogo size={22} />
            <span
              className="text-[15px] font-semibold tracking-[0.08em]"
              style={{ color: 'var(--brand-highlight)' }}
            >
              APEX
            </span>
            <span className="text-[10px] text-[var(--text-muted)] font-medium tracking-wider ml-0.5 hidden sm:inline">
              WEATHER
            </span>
          </div>

          {/* Circuit Selector */}
          <div className="flex-1 max-w-md">
            <CircuitSelector
              circuits={circuits}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          </div>

          {/* Right controls */}
          <div className="flex items-center gap-3">
            <ExportButton circuitId={selectedId} />
            <button
              onClick={() => refetch()}
              disabled={loading}
              className="w-7 h-7 flex items-center justify-center rounded transition-colors"
              style={{
                color: loading ? 'var(--brand-primary)' : 'var(--text-tertiary)',
              }}
              title="Refresh weather data"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className={loading ? "animate-spin" : ""}
              >
                <path d="M21 12a9 9 0 1 1-6.22-8.56" />
                <path d="M21 3v9h-9" />
              </svg>
            </button>
            <div className="flex items-center gap-1.5">
              <span className="w-[5px] h-[5px] rounded-full bg-[var(--accent-green)] live-dot" />
              <span className="text-[9px] uppercase tracking-[0.15em] font-medium text-[var(--text-tertiary)]">
                Live
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* ─── Main Content ─── */}
      <main className="flex-1 px-4 py-5 lg:px-6 lg:py-6">
        <div className="max-w-[1600px] mx-auto">
          {/* Error states */}
          {circuitsError && (
            <div className="data-card p-5 text-center mb-6" style={{ borderColor: 'rgba(191,88,88,0.25)' }}>
              <p className="text-[var(--accent-red)] font-semibold text-sm">Failed to load circuits</p>
              <p className="text-xs text-[var(--text-secondary)] mt-1">{circuitsError}</p>
              <p className="text-[11px] text-[var(--text-tertiary)] mt-2 font-mono">
                {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
              </p>
            </div>
          )}

          {!selectedId && !circuitsError && (
            <div className="data-card p-20 text-center glow-amber">
              <ApexLogo size={44} className="mx-auto mb-5 opacity-80" />
              <h2 className="text-xl font-semibold mb-1" style={{ color: 'var(--brand-highlight)' }}>
                APEX
              </h2>
              <p className="text-[var(--text-secondary)] text-[13px]">Motorsport Weather Intelligence</p>
              <p className="text-[var(--text-muted)] text-[11px] mt-1">Select a circuit to begin</p>
            </div>
          )}

          {selectedId && loading && !weather && (
            <div className="data-card p-20 text-center">
              <div className="inline-block w-5 h-5 border-2 border-[var(--brand-primary)] border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-sm text-[var(--text-secondary)]">Loading weather data…</p>
            </div>
          )}

          {error && (
            <div className="data-card p-4 mb-6" style={{ borderColor: 'rgba(217,175,66,0.2)' }}>
              <p className="text-[var(--accent-yellow)] font-semibold text-sm">Weather data unavailable</p>
              <p className="text-xs text-[var(--text-secondary)] mt-1">{error}</p>
            </div>
          )}

          {weather && selectedCircuit && (
            <div className="space-y-5">
              {/* ─── Circuit Info ─── */}
              <div className="flex items-start justify-between flex-wrap gap-3">
                <div>
                  <div className="flex items-center gap-3">
                    <h2 className="text-lg font-semibold text-[var(--text-primary)] tracking-tight">
                      {weather.circuit_name}
                    </h2>
                    {weather.surface_type && (
                      <span
                        className="text-[9px] px-2 py-[3px] rounded font-medium tracking-wider uppercase"
                        style={{
                          color: 'var(--text-secondary)',
                          background: 'var(--bg-elevated)',
                          border: '1px solid var(--border-color)',
                        }}
                      >
                        {formatSurfaceType(weather.surface_type)}
                      </span>
                    )}
                  </div>
                  <p className="text-[12px] text-[var(--text-secondary)] mt-0.5 font-light">
                    {selectedCircuit.country}
                    {selectedCircuit.length_km ? ` · ${selectedCircuit.length_km} km` : ""}
                    {selectedCircuit.series ? ` · ${selectedCircuit.series}` : ""}
                    <span className="hidden lg:inline text-[var(--text-tertiary)]">
                      {" "}· {selectedCircuit.latitude.toFixed(4)}, {selectedCircuit.longitude.toFixed(4)}
                      {selectedCircuit.altitude_m ? ` · ${selectedCircuit.altitude_m}m` : ""}
                    </span>
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {weather.current && (
                    <span className="text-[10px] text-[var(--text-muted)] font-mono">
                      {new Date(weather.current.observed_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  )}
                  <ConfidenceIndicator confidence={weather.confidence_pct} />
                </div>
              </div>

              {/* ─── Weather Tiles ─── */}
              {weather.current && <WeatherTiles weather={weather.current} />}

              {/* ─── Map Row ─── */}
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                <div className="lg:col-span-3 space-y-2">
                  <CircuitMap
                    circuit={selectedCircuit}
                    corners={weather.circuit_corners || []}
                    windForecast={weather.wind_forecast || []}
                    selectedHourIndex={windHourIndex}
                  />
                  {weather.wind_forecast && weather.wind_forecast.length > 0 && (
                    <TimeSlider
                      windForecast={weather.wind_forecast}
                      selectedIndex={windHourIndex}
                      onIndexChange={setWindHourIndex}
                    />
                  )}
                </div>
                <div className="space-y-3">
                  <AlertsPanel alerts={weather.alerts} />
                  {weather.grip && <GripIndicator grip={weather.grip} />}
                  <SessionInput
                    circuitId={selectedId}
                    sessions={sessions}
                    onAdd={addSession}
                    onRemove={removeSession}
                  />
                </div>
              </div>

              {/* ─── Wind + Surface ─── */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {weather.wind_analysis && (
                  <WindAnalysisPanel
                    wind={weather.wind_analysis}
                    windForecast={weather.wind_forecast || []}
                  />
                )}
                <SurfaceConditionsPanel
                  conditions={interpolatedConditions}
                  drying={weather.drying_estimate}
                  surfaceType={weather.surface_type}
                  sessions={sessions}
                  timeRange={timeRange}
                />
              </div>

              {/* ─── Chart Zoom Controls ─── */}
              <div className="flex items-center justify-between">
                <h3 className="text-[11px] text-[var(--text-muted)] uppercase tracking-[0.12em] font-semibold">
                  Forecast Charts
                </h3>
                <ChartZoomControls
                  zoomLevel={zoomLevel}
                  onZoomChange={setZoomLevel}
                  panOffsetMs={panOffsetMs}
                  onPanChange={setPanOffsetMs}
                  forecastStartMs={forecastStartMs}
                  forecastEndMs={forecastEndMs}
                />
              </div>

              {/* ─── Forecast ─── */}
              <ForecastChart
                forecast={interpolatedForecast}
                sessions={sessions}
                timeRange={timeRange}
              />

              {/* ─── Detail Charts ─── */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <TrackTempChart
                  forecast={interpolatedForecast}
                  surfaceType={weather.surface_type}
                  sessions={sessions}
                  timeRange={timeRange}
                />
                <RainIntensityChart
                  forecast={interpolatedForecast}
                  sessions={sessions}
                  timeRange={timeRange}
                />
              </div>
            </div>
          )}

          {/* Model Comparison Panel */}
          {modelComparison && modelComparison.models.length > 0 && (
            <ModelComparisonPanel data={modelComparison} timeRange={timeRange} />
          )}
        </div>
      </main>
    </div>
  );
}
