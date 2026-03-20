"use client";

import { useState, useRef, useCallback, useMemo } from "react";
import { WeatherForecastPoint, UserSession, TimeRange } from "@/types";
import { sessionOverlap } from "@/lib/sessionUtils";
import { filterByTimeRange, generateTicks } from "@/lib/interpolate";

interface Props {
  forecast: WeatherForecastPoint[];
  surfaceType?: string | null;
  sessions?: UserSession[];
  timeRange: TimeRange;
}

const ZONES = [
  { max: 25, color: "var(--accent-blue)", label: "Cold" },
  { max: 35, color: "var(--accent-green)", label: "Cool" },
  { max: 50, color: "var(--accent-yellow)", label: "Optimal" },
  { max: 999, color: "var(--accent-red)", label: "Hot" },
];

function getZoneColor(trackTemp: number): string {
  for (const zone of ZONES) {
    if (trackTemp < zone.max) return zone.color;
  }
  return "var(--accent-red)";
}

const surfaceLabels: Record<string, string> = {
  standard_asphalt: "Standard",
  high_grip_asphalt: "High-Grip",
  abrasive: "Abrasive",
  low_grip_street: "Street",
  concrete_mix: "Concrete",
};

export default function TrackTempChart({ forecast, surfaceType, sessions, timeRange }: Props) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);
  const chartRef = useRef<HTMLDivElement>(null);

  // Filter to visible range
  const points = useMemo(
    () => timeRange.startMs > 0
      ? filterByTimeRange(forecast, timeRange.startMs, timeRange.endMs)
      : forecast,
    [forecast, timeRange],
  );

  if (points.length === 0) return null;

  const allTemps: number[] = [];
  for (const p of points) {
    if (p.temperature_c != null) allTemps.push(p.temperature_c);
    if (p.track_temperature_c != null) allTemps.push(p.track_temperature_c);
  }
  if (allTemps.length === 0) return null;

  const maxTemp = Math.max(...allTemps);
  const minTemp = Math.min(...allTemps);
  const range = Math.max(maxTemp - minTemp, 10);
  const pad = 3;
  const chartH = 130;

  function tempToY(temp: number): number {
    return chartH - ((temp - minTemp + pad) / (range + pad * 2)) * chartH;
  }

  function buildPath(key: "temperature_c" | "track_temperature_c"): string {
    const segments: string[] = [];
    for (let i = 0; i < points.length; i++) {
      const val = points[i][key];
      if (val == null) continue;
      const x = points.length > 1 ? (i / (points.length - 1)) * 100 : 50;
      const y = tempToY(val);
      segments.push(`${segments.length === 0 ? "M" : "L"} ${x} ${y}`);
    }
    return segments.join(" ");
  }

  // Session bands
  const sessionBands = (sessions || [])
    .map((s) => sessionOverlap(s, timeRange.startMs, timeRange.endMs))
    .filter(Boolean) as { left: number; width: number; name: string; shortName: string; color: string }[];

  // Adaptive ticks
  const ticks = generateTicks(timeRange.startMs, timeRange.endMs);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const rect = chartRef.current?.getBoundingClientRect();
      if (!rect) return;
      const x = (e.clientX - rect.left) / rect.width;
      const idx = Math.round(x * (points.length - 1));
      setHoverIndex(Math.max(0, Math.min(points.length - 1, idx)));
    },
    [points.length],
  );

  const handleMouseLeave = useCallback(() => setHoverIndex(null), []);

  const hp = hoverIndex !== null ? points[hoverIndex] : null;
  const hoverX = hoverIndex !== null && points.length > 1
    ? (hoverIndex / (points.length - 1)) * 100
    : null;

  // Only render circle markers at ~hourly intervals to reduce clutter
  const markerStep = Math.max(1, Math.round(points.length / 24));

  return (
    <div className="data-card p-4">
      <div className="flex items-center justify-between mb-1">
        <h3 className="section-heading">Track Temperature</h3>
        <div className="flex gap-3 text-[9px] text-[var(--text-muted)]">
          <span className="flex items-center gap-1">
            <span className="w-3 h-[2px] rounded inline-block" style={{ backgroundColor: "var(--accent-yellow)" }} />
            Track
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-[2px] rounded inline-block" style={{ backgroundColor: "var(--text-tertiary)", opacity: 0.5 }} />
            Air
          </span>
        </div>
      </div>

      {surfaceType && (
        <p className="text-[9px] text-[var(--text-muted)] mb-3 font-mono">
          {surfaceLabels[surfaceType] || surfaceType}
        </p>
      )}

      {/* Tooltip */}
      {hp && hoverIndex !== null && (
        <div className="flex items-center gap-3 mb-2 px-2 py-1 rounded text-[10px] font-mono tabular-nums" style={{ background: 'var(--bg-inset)', border: '1px solid var(--border-subtle)' }}>
          <span className="text-[var(--text-muted)]">
            {new Date(hp.forecast_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
          <span style={{ color: "var(--accent-yellow)" }}>
            Track: {hp.track_temperature_c?.toFixed(1) ?? "—"}°C
          </span>
          <span className="text-[var(--text-tertiary)]">
            Air: {hp.temperature_c?.toFixed(1) ?? "—"}°C
          </span>
          {hp.track_temperature_c != null && hp.temperature_c != null && (
            <span className="text-[var(--text-muted)]">
              Δ {(hp.track_temperature_c - hp.temperature_c) > 0 ? "+" : ""}{(hp.track_temperature_c - hp.temperature_c).toFixed(1)}°
            </span>
          )}
        </div>
      )}

      <div className="flex gap-2">
        <div className="flex flex-col justify-between text-[8px] text-[var(--text-muted)] w-7 text-right shrink-0 font-mono tabular-nums" style={{ height: `${chartH}px` }}>
          <span>{Math.round(maxTemp + pad)}°</span>
          <span>{Math.round((maxTemp + minTemp) / 2)}°</span>
          <span>{Math.round(minTemp - pad)}°</span>
        </div>

        <div
          ref={chartRef}
          className="relative flex-1 cursor-crosshair"
          style={{ height: `${chartH}px` }}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          {/* Session shading */}
          {sessionBands.map((band, i) => (
            <div
              key={`session-${i}`}
              className="absolute top-0 bottom-0 rounded-sm pointer-events-none"
              style={{
                left: `${band.left}%`,
                width: `${band.width}%`,
                background: `color-mix(in srgb, ${band.color} 12%, transparent)`,
                borderLeft: `1px solid color-mix(in srgb, ${band.color} 25%, transparent)`,
                borderRight: `1px solid color-mix(in srgb, ${band.color} 25%, transparent)`,
                zIndex: 0,
              }}
            >
              <span
                className="absolute top-0.5 left-1 text-[7px] font-semibold tracking-wider uppercase whitespace-nowrap"
                style={{ color: band.color, opacity: 0.7 }}
              >
                {band.shortName}
              </span>
            </div>
          ))}

          <svg
            viewBox={`0 0 100 ${chartH}`}
            preserveAspectRatio="none"
            className="w-full h-full relative"
            style={{ zIndex: 1 }}
          >
            {[0.25, 0.5, 0.75].map((frac) => (
              <line
                key={frac}
                x1="0" y1={chartH * frac}
                x2="100" y2={chartH * frac}
                stroke="var(--border-subtle)"
                strokeWidth="0.3"
                vectorEffect="non-scaling-stroke"
              />
            ))}

            <path
              d={buildPath("temperature_c")}
              fill="none"
              stroke="var(--text-tertiary)"
              strokeWidth="1"
              strokeDasharray="3,3"
              vectorEffect="non-scaling-stroke"
              opacity="0.4"
            />

            <path
              d={buildPath("track_temperature_c")}
              fill="none"
              stroke="var(--accent-yellow)"
              strokeWidth="1.8"
              vectorEffect="non-scaling-stroke"
            />

            {/* Circle markers at hourly intervals only */}
            {points.map((p, i) => {
              if (p.track_temperature_c == null) return null;
              if (i % markerStep !== 0 && i !== points.length - 1) return null;
              const x = points.length > 1 ? (i / (points.length - 1)) * 100 : 50;
              const y = tempToY(p.track_temperature_c);
              return (
                <circle
                  key={i}
                  cx={x}
                  cy={y}
                  r="1.3"
                  fill={getZoneColor(p.track_temperature_c)}
                />
              );
            })}

            {/* Hover cursor line + dots */}
            {hoverX !== null && hp && (
              <>
                <line
                  x1={hoverX} y1={0}
                  x2={hoverX} y2={chartH}
                  stroke="var(--text-muted)"
                  strokeWidth="0.5"
                  strokeDasharray="2,2"
                  vectorEffect="non-scaling-stroke"
                  opacity="0.6"
                />
                {hp.track_temperature_c != null && (
                  <circle
                    cx={hoverX}
                    cy={tempToY(hp.track_temperature_c)}
                    r="2.5"
                    fill="var(--accent-yellow)"
                    stroke="var(--bg-primary)"
                    strokeWidth="1"
                    vectorEffect="non-scaling-stroke"
                  />
                )}
                {hp.temperature_c != null && (
                  <circle
                    cx={hoverX}
                    cy={tempToY(hp.temperature_c)}
                    r="2"
                    fill="var(--text-tertiary)"
                    stroke="var(--bg-primary)"
                    strokeWidth="1"
                    vectorEffect="non-scaling-stroke"
                    opacity="0.7"
                  />
                )}
              </>
            )}
          </svg>
        </div>
      </div>

      {/* Adaptive time axis */}
      <div className="relative h-4 mt-2 ml-9">
        {ticks.map((tickMs) => {
          const pct = ((tickMs - timeRange.startMs) / (timeRange.endMs - timeRange.startMs)) * 100;
          const d = new Date(tickMs);
          return (
            <span
              key={tickMs}
              className="absolute text-[8px] text-[var(--text-muted)] font-mono"
              style={{ left: `${pct}%`, transform: "translateX(-50%)" }}
            >
              {d.getHours().toString().padStart(2, "0")}:{d.getMinutes().toString().padStart(2, "0")}
            </span>
          );
        })}
      </div>

      <div className="flex gap-3 mt-3 text-[8px] text-[var(--text-muted)] flex-wrap">
        {ZONES.map((zone) => (
          <span key={zone.label} className="flex items-center gap-1">
            <span
              className="w-[5px] h-[5px] rounded-full inline-block"
              style={{ backgroundColor: zone.color }}
            />
            {zone.label}
          </span>
        ))}
      </div>
    </div>
  );
}
