"use client";

import { TrackConditionPoint, DryingEstimate, UserSession, TimeRange } from "@/types";
import { sessionOverlap } from "@/lib/sessionUtils";
import { filterByTimeRange, generateTicks } from "@/lib/interpolate";

interface Props {
  conditions: TrackConditionPoint[];
  drying: DryingEstimate | null;
  surfaceType?: string | null;
  sessions?: UserSession[];
  timeRange: TimeRange;
}

const CONDITION_STYLES: Record<string, { color: string; label: string }> = {
  dry: { color: "var(--accent-green)", label: "Dry" },
  damp: { color: "var(--accent-yellow)", label: "Damp" },
  wet: { color: "var(--accent-blue)", label: "Wet" },
  very_wet: { color: "#7c6fd4", label: "Very Wet" },
  flooded: { color: "var(--accent-red)", label: "Flooded" },
};

const SURFACE_INFO: Record<string, { drainage: string; porosity: string }> = {
  standard_asphalt: { drainage: "Normal", porosity: "50%" },
  high_grip_asphalt: { drainage: "Good", porosity: "60%" },
  abrasive: { drainage: "Excellent", porosity: "70%" },
  low_grip_street: { drainage: "Poor", porosity: "30%" },
  concrete_mix: { drainage: "Below Avg", porosity: "40%" },
};

const SURFACE_LABELS: Record<string, string> = {
  standard_asphalt: "Standard Asphalt",
  high_grip_asphalt: "High-Grip Asphalt",
  abrasive: "Abrasive",
  low_grip_street: "Street Circuit",
  concrete_mix: "Concrete Mix",
};

export default function SurfaceConditionsPanel({ conditions, drying, surfaceType, sessions, timeRange }: Props) {
  // BUG FIX: Use forecast simulation's condition (accounts for accumulated rain)
  // instead of drying.condition (only knows current intensity)
  const currentCondition = conditions.length > 0 ? conditions[0].condition : (drying?.condition || "dry");
  const style = CONDITION_STYLES[currentCondition] || CONDITION_STYLES.dry;
  const isDry = currentCondition === "dry";

  // Filter conditions to visible time range
  const visible = timeRange.startMs > 0
    ? filterByTimeRange(conditions, timeRange.startMs, timeRange.endMs)
    : conditions;

  // Compute session bands for timeline overlay
  const sessionBands = visible.length > 0
    ? (sessions || [])
        .map((s) => sessionOverlap(s, timeRange.startMs, timeRange.endMs))
        .filter(Boolean) as { left: number; width: number; name: string; shortName: string; color: string }[]
    : [];

  // Adaptive time axis ticks
  const ticks = timeRange.startMs > 0 ? generateTicks(timeRange.startMs, timeRange.endMs) : [];

  return (
    <div className="data-card p-4">
      <h3 className="section-heading mb-3">Surface Conditions</h3>

      {/* Status row */}
      <div className="flex items-start gap-4 mb-4">
        <div
          className="flex items-center justify-center px-3 py-1.5 rounded text-[12px] font-bold uppercase tracking-wider"
          style={{
            color: style.color,
            backgroundColor: `color-mix(in srgb, ${style.color} 10%, transparent)`,
            border: `1px solid color-mix(in srgb, ${style.color} 20%, transparent)`,
          }}
        >
          {style.label}
        </div>

        {!isDry && drying && (
          <div className="flex-1 grid grid-cols-2 gap-x-4 gap-y-1.5">
            <div>
              <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider">Water Depth</div>
              <div className="text-[13px] font-semibold tabular-nums">{drying.water_depth_mm.toFixed(2)} mm</div>
            </div>
            <div>
              <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider">Drying Rate</div>
              <div className="text-[13px] font-semibold tabular-nums">{drying.drying_rate_mm_hr.toFixed(2)} mm/hr</div>
            </div>
            {drying.damp_minutes > 0 && (
              <div>
                <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider">Damp in</div>
                <div className="text-[13px] font-semibold tabular-nums" style={{ color: "var(--accent-yellow)" }}>
                  {drying.damp_minutes} min
                </div>
              </div>
            )}
            {drying.dry_minutes > 0 && (
              <div>
                <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider">Dry in</div>
                <div className="text-[13px] font-semibold tabular-nums" style={{ color: "var(--accent-green)" }}>
                  {drying.dry_minutes} min
                </div>
              </div>
            )}
          </div>
        )}

        {isDry && (
          <div className="flex-1 flex items-center">
            <span className="text-[12px] text-[var(--text-tertiary)]">Track surface is dry. No standing water.</span>
          </div>
        )}
      </div>

      {/* Timeline */}
      {visible.length > 0 && (
        <>
          <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-[0.12em] mb-1.5">Surface Timeline</div>
          <div className="relative">
            {sessionBands.map((band, i) => (
              <div
                key={`session-${i}`}
                className="absolute rounded-sm pointer-events-none"
                style={{
                  left: `${band.left}%`,
                  width: `${band.width}%`,
                  top: 0,
                  bottom: 0,
                  background: `color-mix(in srgb, ${band.color} 15%, transparent)`,
                  borderLeft: `1px solid color-mix(in srgb, ${band.color} 30%, transparent)`,
                  borderRight: `1px solid color-mix(in srgb, ${band.color} 30%, transparent)`,
                  zIndex: 2,
                }}
              >
                <span
                  className="absolute -top-3.5 left-0 text-[7px] font-semibold tracking-wider uppercase whitespace-nowrap"
                  style={{ color: band.color, opacity: 0.8 }}
                >
                  {band.shortName}
                </span>
              </div>
            ))}
            <div className="flex gap-[1px] rounded-sm overflow-hidden mb-1" style={{ height: "16px" }}>
              {visible.map((c, i) => {
                const s = CONDITION_STYLES[c.condition] || CONDITION_STYLES.dry;
                return (
                  <div
                    key={i}
                    className="flex-1 transition-opacity hover:opacity-90"
                    style={{ backgroundColor: s.color, opacity: 0.45 }}
                    title={`${new Date(c.forecast_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} — ${s.label} | Rain: ${c.precipitation_intensity.toFixed(1)} mm/hr | Total: ${c.accumulated_rain_mm.toFixed(1)} mm`}
                  />
                );
              })}
            </div>
            {/* Adaptive time axis */}
            <div className="relative h-3 mb-3">
              {ticks.map((tickMs) => {
                const pct = ((tickMs - timeRange.startMs) / (timeRange.endMs - timeRange.startMs)) * 100;
                return (
                  <span
                    key={tickMs}
                    className="absolute text-[8px] text-[var(--text-muted)] font-mono"
                    style={{ left: `${pct}%`, transform: "translateX(-50%)" }}
                  >
                    {new Date(tickMs).getHours().toString().padStart(2, "0")}:{new Date(tickMs).getMinutes().toString().padStart(2, "0")}
                  </span>
                );
              })}
            </div>
          </div>

          {/* Rain accumulation */}
          {visible.some((c) => c.accumulated_rain_mm > 0.01) && (
            <>
              <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-[0.12em] mb-1.5">Rain Accumulation</div>
              <div className="flex gap-[1px] items-end" style={{ height: "32px" }}>
                {visible.map((c, i) => {
                  const maxRain = Math.max(1, ...visible.map((x) => x.accumulated_rain_mm));
                  const h = c.accumulated_rain_mm > 0.01 ? Math.max(4, (c.accumulated_rain_mm / maxRain) * 100) : 0;
                  return (
                    <div key={i} className="flex-1 flex justify-end flex-col h-full">
                      <div
                        className="w-full rounded-t-sm"
                        style={{ height: `${h}%`, backgroundColor: "var(--accent-cyan)", opacity: 0.4 }}
                      />
                    </div>
                  );
                })}
              </div>
              <div className="text-[8px] text-[var(--text-muted)] text-right mt-0.5 mb-2 font-mono">mm</div>
            </>
          )}
        </>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-2" style={{ borderTop: '1px solid var(--border-subtle)' }}>
        {surfaceType && SURFACE_INFO[surfaceType] && (
          <div className="text-[10px] text-[var(--text-muted)]">
            {SURFACE_LABELS[surfaceType] || surfaceType} · {SURFACE_INFO[surfaceType].drainage} drain · {SURFACE_INFO[surfaceType].porosity}
          </div>
        )}
        <div className="flex gap-2 text-[8px] text-[var(--text-muted)]">
          {Object.entries(CONDITION_STYLES).map(([key, s]) => (
            <span key={key} className="flex items-center gap-0.5">
              <span className="w-[5px] h-[5px] rounded-full" style={{ backgroundColor: s.color, opacity: 0.6 }} />
              {s.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
