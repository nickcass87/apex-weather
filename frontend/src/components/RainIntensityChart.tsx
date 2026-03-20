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

function getIntensityColor(intensity: number): string {
  if (intensity < 0.1) return "var(--border-color)";
  if (intensity < 2.5) return "var(--accent-blue)";
  if (intensity < 7.5) return "var(--accent-yellow)";
  return "var(--accent-red)";
}

function getIntensityLabel(intensity: number): string {
  if (intensity < 0.1) return "None";
  if (intensity < 2.5) return "Light";
  if (intensity < 7.5) return "Moderate";
  return "Heavy";
}

/** Downsample points by averaging into groups */
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

export default function RainIntensityChart({ forecast, sessions, timeRange }: Props) {
  if (forecast.length === 0) return null;

  const visible = useMemo(
    () => timeRange.startMs > 0
      ? filterByTimeRange(forecast, timeRange.startMs, timeRange.endMs)
      : forecast,
    [forecast, timeRange],
  );

  const points = useMemo(() => downsample(visible, 48), [visible]);

  if (points.length === 0) return null;

  const maxIntensity = Math.max(
    1,
    ...points.map((p) => p.precipitation_intensity ?? 0),
  );

  const hasAnyPrecip = points.some(
    (p) => (p.precipitation_intensity ?? 0) >= 0.1 || (p.precipitation_probability ?? 0) > 20,
  );

  // Session overlays
  const sessionBands = (sessions || [])
    .map((s) => sessionOverlap(s, timeRange.startMs, timeRange.endMs))
    .filter(Boolean) as { left: number; width: number; name: string; shortName: string; color: string }[];

  // Adaptive ticks
  const ticks = generateTicks(timeRange.startMs, timeRange.endMs);

  return (
    <div className="data-card p-4">
      <h3 className="section-heading mb-3">Precipitation</h3>

      {!hasAnyPrecip ? (
        <div className="h-24 flex items-center justify-center text-[var(--text-muted)] text-[12px]">
          No precipitation expected
        </div>
      ) : (
        <>
          <div className="relative flex gap-[1px] items-end" style={{ height: "100px" }}>
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
            {points.map((point, i) => {
              const intensity = point.precipitation_intensity ?? 0;
              const probability = point.precipitation_probability ?? 0;
              const barPct =
                intensity < 0.1
                  ? 2
                  : Math.max(8, (intensity / maxIntensity) * 100);

              return (
                <div
                  key={i}
                  className="flex-1 flex flex-col items-center justify-end h-full"
                  style={{ position: "relative", zIndex: 1 }}
                >
                  {probability > 0 && (
                    <span className="text-[7px] text-[var(--text-muted)] mb-0.5 leading-none tabular-nums">
                      {probability.toFixed(0)}%
                    </span>
                  )}

                  <div
                    className="w-full rounded-t-sm"
                    style={{
                      height: `${barPct}%`,
                      backgroundColor: getIntensityColor(intensity),
                      opacity:
                        intensity < 0.1
                          ? 0.2
                          : Math.max(0.6, 0.6 + (intensity / maxIntensity) * 0.4),
                    }}
                    title={`${new Date(point.forecast_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} — ${intensity.toFixed(1)} mm/hr (${getIntensityLabel(intensity)}) | ${probability.toFixed(0)}%`}
                  />

                  {intensity >= 0.1 && (
                    <span className="text-[7px] text-[var(--text-muted)] mt-0.5 leading-none tabular-nums font-mono">
                      {intensity.toFixed(1)}
                    </span>
                  )}
                </div>
              );
            })}
          </div>

          {/* Adaptive time axis */}
          <div className="relative h-4 mt-1.5">
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
        </>
      )}

      <div className="flex gap-3 mt-3 text-[8px] text-[var(--text-muted)] flex-wrap">
        <span className="flex items-center gap-1">
          <span className="w-[5px] h-[5px] rounded-full inline-block" style={{ backgroundColor: "var(--accent-blue)" }} />
          Light
        </span>
        <span className="flex items-center gap-1">
          <span className="w-[5px] h-[5px] rounded-full inline-block" style={{ backgroundColor: "var(--accent-yellow)" }} />
          Moderate
        </span>
        <span className="flex items-center gap-1">
          <span className="w-[5px] h-[5px] rounded-full inline-block" style={{ backgroundColor: "var(--accent-red)" }} />
          Heavy
        </span>
        <span className="text-[var(--text-muted)] opacity-60">opacity = intensity</span>
      </div>
    </div>
  );
}
