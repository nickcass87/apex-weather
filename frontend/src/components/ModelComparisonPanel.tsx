"use client";

import { ModelComparisonResponse, TimeRange } from "@/types";
import { generateTicks } from "@/lib/interpolate";

interface Props {
  data: ModelComparisonResponse;
  timeRange: TimeRange;
}

/** Filter model points to visible time range. */
function filterPoints<T extends { time: string }>(
  points: T[],
  startMs: number,
  endMs: number,
): T[] {
  return points.filter((p) => {
    const t = new Date(p.time).getTime();
    return t >= startMs && t <= endMs;
  });
}

/** Compute consensus summary for rain timing. */
function rainConsensus(data: ModelComparisonResponse, startMs: number, endMs: number): string {
  const models = data.models;
  if (models.length === 0) return "";

  // For each model, find hours with precip > 0.1mm
  const modelRainHours = models.map((m) => {
    const visible = filterPoints(m.points, startMs, endMs);
    return new Set(
      visible
        .filter((p) => p.precip_mm > 0.1)
        .map((p) => new Date(p.time).getHours()),
    );
  });

  // Find hours where ALL models agree on rain
  const allRainHours = [...modelRainHours[0]].filter((h) =>
    modelRainHours.every((s) => s.has(h)),
  );

  // Find hours where ANY model shows rain
  const anyRainHours = new Set<number>();
  modelRainHours.forEach((s) => s.forEach((h) => anyRainHours.add(h)));

  if (anyRainHours.size === 0) return "All models agree: dry conditions expected";
  if (allRainHours.length === anyRainHours.size && anyRainHours.size > 0) {
    const sorted = [...anyRainHours].sort((a, b) => a - b);
    return `All models agree: rain ${fmtHour(sorted[0])}–${fmtHour(sorted[sorted.length - 1] + 1)}`;
  }

  // Count disagreement
  const onlyOneModel = [...anyRainHours].filter(
    (h) => modelRainHours.filter((s) => s.has(h)).length === 1,
  );
  if (onlyOneModel.length > anyRainHours.size * 0.5) {
    return "Models disagree significantly on rain timing";
  }
  return "Models partially agree on rain timing — check details below";
}

function fmtHour(h: number): string {
  return `${(h % 24).toString().padStart(2, "0")}:00`;
}

export default function ModelComparisonPanel({ data, timeRange }: Props) {
  if (!data.models.length) return null;

  const ticks = timeRange.startMs > 0 ? generateTicks(timeRange.startMs, timeRange.endMs) : [];
  const duration = timeRange.endMs - timeRange.startMs;
  const consensus = rainConsensus(data, timeRange.startMs, timeRange.endMs);

  return (
    <div className="data-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="section-heading">Model Comparison</h3>
        <div className="flex items-center gap-3">
          {data.models.map((m) => (
            <span key={m.model_id} className="flex items-center gap-1 text-[9px] font-semibold tracking-wider">
              <span className="w-[8px] h-[3px] rounded-full" style={{ backgroundColor: m.color }} />
              <span style={{ color: m.color }}>{m.label}</span>
            </span>
          ))}
        </div>
      </div>

      {/* Consensus badge */}
      {consensus && (
        <div
          className="text-[10px] px-2.5 py-1 rounded mb-3 font-medium"
          style={{
            backgroundColor: consensus.includes("disagree")
              ? "color-mix(in srgb, var(--accent-yellow) 10%, transparent)"
              : consensus.includes("dry")
                ? "color-mix(in srgb, var(--accent-green) 10%, transparent)"
                : "color-mix(in srgb, var(--accent-blue) 10%, transparent)",
            color: consensus.includes("disagree")
              ? "var(--accent-yellow)"
              : consensus.includes("dry")
                ? "var(--accent-green)"
                : "var(--accent-blue)",
            border: `1px solid ${
              consensus.includes("disagree")
                ? "color-mix(in srgb, var(--accent-yellow) 20%, transparent)"
                : consensus.includes("dry")
                  ? "color-mix(in srgb, var(--accent-green) 20%, transparent)"
                  : "color-mix(in srgb, var(--accent-blue) 20%, transparent)"
            }`,
          }}
        >
          {consensus}
        </div>
      )}

      {/* Rain timing comparison — the most critical chart */}
      <div className="mb-4">
        <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-[0.12em] mb-1.5">
          Precipitation (mm/hr)
        </div>
        <div className="space-y-1">
          {data.models.map((model) => {
            const visible = filterPoints(model.points, timeRange.startMs, timeRange.endMs);
            const maxPrecip = Math.max(
              1,
              ...data.models.flatMap((m) =>
                filterPoints(m.points, timeRange.startMs, timeRange.endMs).map((p) => p.precip_mm),
              ),
            );

            return (
              <div key={model.model_id} className="flex items-center gap-2">
                <span
                  className="text-[8px] font-semibold w-[40px] text-right shrink-0"
                  style={{ color: model.color }}
                >
                  {model.label}
                </span>
                <div className="flex-1 flex gap-[1px] items-end" style={{ height: "18px" }}>
                  {visible.map((p, i) => {
                    const h = p.precip_mm > 0.01
                      ? Math.max(3, (p.precip_mm / maxPrecip) * 100)
                      : 0;
                    return (
                      <div key={i} className="flex-1 flex flex-col justify-end h-full">
                        <div
                          className="w-full rounded-t-sm"
                          style={{
                            height: `${h}%`,
                            backgroundColor: model.color,
                            opacity: p.precip_mm > 0.5 ? 0.8 : 0.5,
                          }}
                          title={`${new Date(p.time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} — ${p.precip_mm.toFixed(1)} mm`}
                        />
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Temperature overlay */}
      <div className="mb-4">
        <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-[0.12em] mb-1.5">
          Temperature (°C)
        </div>
        <OverlayLineChart
          models={data.models}
          timeRange={timeRange}
          field="temp_c"
          unit="°"
          height={60}
        />
      </div>

      {/* Wind speed overlay */}
      <div className="mb-2">
        <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-[0.12em] mb-1.5">
          Wind Speed (km/h)
        </div>
        <OverlayLineChart
          models={data.models}
          timeRange={timeRange}
          field="wind_kmh"
          unit=""
          height={50}
        />
      </div>

      {/* Shared time axis */}
      <div className="relative h-3">
        {ticks.map((tickMs) => {
          const pct = ((tickMs - timeRange.startMs) / duration) * 100;
          return (
            <span
              key={tickMs}
              className="absolute text-[8px] text-[var(--text-muted)] font-mono"
              style={{ left: `${pct}%`, transform: "translateX(-50%)" }}
            >
              {new Date(tickMs).getHours().toString().padStart(2, "0")}:
              {new Date(tickMs).getMinutes().toString().padStart(2, "0")}
            </span>
          );
        })}
      </div>
    </div>
  );
}

/** SVG overlay line chart for 3 models on the same axis. */
function OverlayLineChart({
  models,
  timeRange,
  field,
  unit,
  height,
}: {
  models: ModelComparisonResponse["models"];
  timeRange: TimeRange;
  field: "temp_c" | "wind_kmh";
  unit: string;
  height: number;
}) {
  // Gather all visible points across models to compute shared Y range
  const allValues: number[] = [];
  const modelVisibles = models.map((m) => {
    const vis = filterPoints(m.points, timeRange.startMs, timeRange.endMs);
    vis.forEach((p) => allValues.push(p[field]));
    return vis;
  });

  if (allValues.length === 0) return <div style={{ height }} />;

  const yMin = Math.min(...allValues);
  const yMax = Math.max(...allValues);
  const yRange = Math.max(1, yMax - yMin);
  const pad = yRange * 0.1;
  const effMin = yMin - pad;
  const effMax = yMax + pad;
  const effRange = effMax - effMin;

  const W = 1000; // SVG viewBox width
  const H = height;

  return (
    <div className="relative">
      {/* Y-axis labels */}
      <span className="absolute left-0 top-0 text-[8px] text-[var(--text-muted)] font-mono">
        {Math.round(yMax)}{unit}
      </span>
      <span className="absolute left-0 bottom-0 text-[8px] text-[var(--text-muted)] font-mono">
        {Math.round(yMin)}{unit}
      </span>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        style={{ height: `${H}px` }}
        preserveAspectRatio="none"
      >
        {models.map((model, mi) => {
          const vis = modelVisibles[mi];
          if (vis.length < 2) return null;

          const pathData = vis
            .map((p, i) => {
              const x = ((new Date(p.time).getTime() - timeRange.startMs) / (timeRange.endMs - timeRange.startMs)) * W;
              const y = H - ((p[field] - effMin) / effRange) * H;
              return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
            })
            .join(" ");

          return (
            <path
              key={model.model_id}
              d={pathData}
              fill="none"
              stroke={model.color}
              strokeWidth="1.5"
              opacity="0.7"
            />
          );
        })}
      </svg>
    </div>
  );
}
