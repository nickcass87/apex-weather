"use client";

import { useMemo } from "react";
import { WeatherForecastPoint, UserSession, TimeRange } from "@/types";
import { sessionOverlap } from "@/lib/sessionUtils";
import { filterByTimeRange, generateTicks } from "@/lib/interpolate";

interface Props {
  forecast: WeatherForecastPoint[];
  sessions?: UserSession[];
  timeRange: TimeRange;
}

/** Downsample points into N groups by averaging numeric fields */
function downsample(points: WeatherForecastPoint[], maxBars: number): WeatherForecastPoint[] {
  if (points.length <= maxBars) return points;
  const groupSize = Math.ceil(points.length / maxBars);
  const result: WeatherForecastPoint[] = [];
  for (let i = 0; i < points.length; i += groupSize) {
    const group = points.slice(i, i + groupSize);
    const avg = (key: keyof WeatherForecastPoint) => {
      const vals = group.map((p) => p[key] as number | null).filter((v) => v != null) as number[];
      return vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
    };
    result.push({
      forecast_time: group[Math.floor(group.length / 2)].forecast_time,
      temperature_c: avg("temperature_c"),
      humidity_pct: avg("humidity_pct"),
      wind_speed_kmh: avg("wind_speed_kmh"),
      wind_direction_deg: avg("wind_direction_deg"),
      precipitation_probability: avg("precipitation_probability"),
      precipitation_intensity: avg("precipitation_intensity"),
      cloud_cover_pct: avg("cloud_cover_pct"),
      weather_code: group[0].weather_code,
      track_temperature_c: avg("track_temperature_c"),
    });
  }
  return result;
}

export default function ForecastChart({ forecast, sessions, timeRange }: Props) {
  if (forecast.length === 0) return null;

  const visible = useMemo(
    () => timeRange.startMs > 0
      ? filterByTimeRange(forecast, timeRange.startMs, timeRange.endMs)
      : forecast,
    [forecast, timeRange],
  );

  const points = useMemo(() => downsample(visible, 48), [visible]);

  if (points.length === 0) return null;

  const maxTemp = Math.max(...points.map((p) => p.temperature_c ?? 0));
  const minTemp = Math.min(...points.map((p) => p.temperature_c ?? 0));
  const tempRange = Math.max(maxTemp - minTemp, 5);

  // Precipitation scale — normalise bars against the visible window max (floor 1 mm so light rain shows)
  const maxPrecip = Math.max(1, ...points.map((p) => p.precipitation_intensity ?? 0));

  // Session overlays
  const sessionBands = (sessions || [])
    .map((s) => sessionOverlap(s, timeRange.startMs, timeRange.endMs))
    .filter(Boolean) as { left: number; width: number; name: string; shortName: string; color: string }[];

  // Adaptive ticks
  const ticks = generateTicks(timeRange.startMs, timeRange.endMs);

  return (
    <div className="data-card p-4">
      <h3 className="section-heading mb-3">Forecast</h3>
      <div className="relative flex gap-[3px] items-end h-32">
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
        {points.map((point, i) => {
          const temp = point.temperature_c ?? 0;
          const height = ((temp - minTemp) / tempRange) * 65 + 35;
          const rainProb = point.precipitation_probability ?? 0;
          const intensity = point.precipitation_intensity ?? 0;
          const isRaining = intensity > 0.05;
          const isLikelyRain = rainProb >= 40;

          // Determine bar color — make rain unmissable
          let barColor = "var(--accent-green)";
          let barOpacity = 0.6;
          if (isRaining) {
            barColor = "#3b82f6"; // bright blue
            barOpacity = 0.85;
          } else if (isLikelyRain) {
            barColor = "#f59e0b"; // amber
            barOpacity = 0.75;
          } else if (rainProb > 15) {
            barColor = "#a3e635"; // yellow-green
            barOpacity = 0.65;
          }

          // Precipitation bar height — min 15% so even drizzle is visible
          const precipBarPct = intensity > 0.01
            ? Math.max(15, (intensity / maxPrecip) * 100)
            : rainProb > 5
              ? Math.max(5, (rainProb / 100) * 12) // ghost bar for probability
              : 0;

          const precipColor = intensity >= 2.5
            ? "#2563eb"
            : intensity >= 0.5
              ? "#3b82f6"
              : intensity > 0.01
                ? "#60a5fa"
                : "#60a5fa44"; // faint for probability-only

          return (
            <div key={i} className="flex-1 flex flex-col items-center gap-0.5 relative">
              {/* Rain label — mm if raining, % if probable */}
              <span className="text-[8px] tabular-nums font-medium leading-none" style={{
                color: isRaining ? "#60a5fa" : rainProb > 0 ? "var(--text-muted)" : "transparent",
              }}>
                {isRaining
                  ? `${intensity.toFixed(1)}mm`
                  : rainProb > 0
                    ? `${rainProb.toFixed(0)}%`
                    : "\u00A0"}
              </span>
              {/* Temperature bar */}
              <div className="w-full relative" style={{ height: `${height}%` }}>
                <div
                  className="w-full h-full rounded-t-sm"
                  style={{ backgroundColor: barColor, opacity: barOpacity }}
                />
              </div>
              <span className="text-[9px] text-[var(--text-tertiary)] tabular-nums font-medium">
                {temp.toFixed(0)}°
              </span>
              {/* Precipitation intensity bar — sits below temp label */}
              <div className="w-full" style={{ height: "16px", display: "flex", alignItems: "flex-end" }}>
                {precipBarPct > 0 && (
                  <div
                    className="w-full rounded-t-sm"
                    style={{
                      height: `${precipBarPct}%`,
                      backgroundColor: precipColor,
                      opacity: intensity > 0.01 ? 0.85 : 0.4,
                    }}
                    title={intensity > 0.01
                      ? `${intensity.toFixed(2)} mm/hr`
                      : `${rainProb}% probability`}
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>
      {/* Adaptive time axis */}
      <div className="relative h-4 mt-1">
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
      {/* Session markers */}
      {sessions && sessions.length > 0 && (
        <div className="flex gap-1.5 mt-2 flex-wrap">
          {sessions.map((s) => {
            const sMs = new Date(s.startTime).getTime();
            if (sMs < timeRange.startMs || sMs > timeRange.endMs) return null;
            return (
              <span
                key={s.id}
                className="text-[8px] px-1.5 py-[2px] rounded font-medium"
                style={{
                  color: 'var(--text-secondary)',
                  background: 'var(--bg-inset)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                {s.name} {new Date(s.startTime).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            );
          })}
        </div>
      )}
      <div className="flex gap-3 mt-2.5 text-[8px] text-[var(--text-muted)]">
        <span className="flex items-center gap-1"><span className="w-[5px] h-[5px] rounded-full bg-[var(--accent-green)]" />Dry</span>
        <span className="flex items-center gap-1"><span className="w-[5px] h-[5px] rounded-full bg-[var(--accent-yellow)]" />Possible</span>
        <span className="flex items-center gap-1"><span className="w-[5px] h-[5px] rounded-full bg-[var(--accent-blue)]" />Likely rain</span>
        <span className="flex items-center gap-1"><span className="w-[5px] h-[5px] rounded-full bg-[var(--accent-blue)] ring-1 ring-[var(--accent-blue)]" />Active rain</span>
      </div>
    </div>
  );
}
