"use client";

import { NowcastResponse } from "@/types";

interface Props {
  nowcast: NowcastResponse;
}

const PRECIP_TYPE_LABEL: Record<number, string> = {
  0: "",
  1: "Rain",
  2: "Snow",
  3: "Freezing",
  4: "Ice",
};

function precipTypeColor(type: number | null): string {
  if (type === 2) return "var(--accent-blue)";
  if (type === 3 || type === 4) return "#a78bfa";
  return "var(--accent-blue)";
}

export default function NowcastPanel({ nowcast }: Props) {
  if (!nowcast || nowcast.points.length === 0) return null;

  const maxIntensity = Math.max(0.5, ...nowcast.points.map(p => p.precipitation_intensity ?? 0));
  const hasAnyRain = nowcast.has_rain_60min;

  return (
    <div className="data-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="section-heading">1-Min Nowcast</h3>
        {hasAnyRain ? (
          <span
            className="text-[9px] px-2 py-[3px] rounded font-semibold uppercase tracking-wider"
            style={{
              color: "var(--accent-red)",
              backgroundColor: "color-mix(in srgb, var(--accent-red) 12%, transparent)",
              border: "1px solid color-mix(in srgb, var(--accent-red) 20%, transparent)",
            }}
          >
            Rain detected
          </span>
        ) : (
          <span
            className="text-[9px] px-2 py-[3px] rounded font-semibold uppercase tracking-wider"
            style={{
              color: "var(--accent-green)",
              backgroundColor: "color-mix(in srgb, var(--accent-green) 12%, transparent)",
              border: "1px solid color-mix(in srgb, var(--accent-green) 20%, transparent)",
            }}
          >
            Clear 60 min
          </span>
        )}
      </div>

      {nowcast.rain_onset_minutes !== null && (
        <div className="text-[11px] text-[var(--accent-yellow)] mb-3 font-medium">
          Rain onset in {nowcast.rain_onset_minutes} min · Peak {nowcast.peak_intensity_mmhr.toFixed(1)} mm/hr
        </div>
      )}

      {/* 60-minute bar chart */}
      <div className="flex gap-[1px] items-end" style={{ height: "48px" }}>
        {nowcast.points.map((point, i) => {
          const intensity = point.precipitation_intensity ?? 0;
          const barPct = intensity < 0.05
            ? 3
            : Math.max(8, (intensity / maxIntensity) * 100);
          const color = precipTypeColor(point.precip_type);
          const isNow = i === 0;
          return (
            <div
              key={i}
              className="flex-1 rounded-t-sm"
              style={{
                height: `${barPct}%`,
                backgroundColor: intensity < 0.05 ? "var(--border-color)" : color,
                opacity: intensity < 0.05 ? 0.3 : Math.max(0.5, 0.5 + (intensity / maxIntensity) * 0.5),
                outline: isNow ? "1px solid var(--brand-primary)" : "none",
              }}
              title={`${i}min: ${intensity.toFixed(2)} mm/hr${point.precip_type ? ` (${PRECIP_TYPE_LABEL[point.precip_type]})` : ""}`}
            />
          );
        })}
      </div>

      {/* Time axis — mark every 15 minutes */}
      <div className="relative h-4 mt-1">
        {[0, 15, 30, 45, 60].map((min) => {
          const idx = Math.min(min, nowcast.points.length - 1);
          if (idx >= nowcast.points.length) return null;
          const pct = (min / 60) * 100;
          return (
            <span
              key={min}
              className="absolute text-[8px] text-[var(--text-muted)] font-mono"
              style={{ left: `${pct}%`, transform: "translateX(-50%)" }}
            >
              {min === 0 ? "now" : `+${min}m`}
            </span>
          );
        })}
      </div>

      <div className="flex gap-3 mt-2 text-[8px] text-[var(--text-muted)]">
        <span className="flex items-center gap-1">
          <span className="w-[5px] h-[5px] rounded-full inline-block bg-[var(--accent-blue)]" />
          Rain
        </span>
        <span className="flex items-center gap-1">
          <span className="w-[5px] h-[5px] rounded-full inline-block" style={{ backgroundColor: "#a78bfa" }} />
          Snow/Ice
        </span>
        <span className="opacity-60">1-min intervals · Tomorrow.io nowcast</span>
      </div>
    </div>
  );
}
