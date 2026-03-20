"use client";

import { WindAnalysis, WindForecastPoint } from "@/types";

interface Props {
  wind: WindAnalysis;
  windForecast: WindForecastPoint[];
}

function impactColor(level: string): string {
  if (level === "critical" || level === "high") return "var(--accent-red)";
  if (level === "moderate") return "var(--accent-yellow)";
  return "var(--accent-green)";
}

export default function WindAnalysisPanel({ wind, windForecast }: Props) {
  return (
    <div className="data-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="section-heading">Wind Analysis</h3>
        <span
          className="text-[9px] px-2 py-[3px] rounded font-semibold uppercase tracking-wider"
          style={{
            color: impactColor(wind.impact_level),
            backgroundColor: `color-mix(in srgb, ${impactColor(wind.impact_level)} 12%, transparent)`,
            border: `1px solid color-mix(in srgb, ${impactColor(wind.impact_level)} 20%, transparent)`,
          }}
        >
          {wind.impact_level}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        {/* Compass */}
        <div className="flex flex-col items-center">
          <div className="relative w-20 h-20">
            <svg viewBox="0 0 100 100" className="w-full h-full">
              <circle cx="50" cy="50" r="45" fill="none" stroke="var(--border-color)" strokeWidth="0.8" />
              <circle cx="50" cy="50" r="30" fill="none" stroke="var(--border-subtle)" strokeWidth="0.5" strokeDasharray="2,3" />
              <text x="50" y="11" textAnchor="middle" fill="var(--text-muted)" fontSize="7" fontWeight="600">N</text>
              <text x="92" y="53" textAnchor="middle" fill="var(--text-muted)" fontSize="7">E</text>
              <text x="50" y="97" textAnchor="middle" fill="var(--text-muted)" fontSize="7">S</text>
              <text x="8" y="53" textAnchor="middle" fill="var(--text-muted)" fontSize="7">W</text>
              <g transform={`rotate(${wind.direction_deg}, 50, 50)`}>
                <line x1="50" y1="68" x2="50" y2="22" stroke="var(--brand-primary)" strokeWidth="2" strokeLinecap="round" />
                <polygon points="50,17 45,27 55,27" fill="var(--brand-primary)" />
              </g>
              <circle cx="50" cy="50" r="2.5" fill="var(--brand-primary)" opacity="0.6" />
            </svg>
          </div>
          <span className="text-[11px] text-[var(--text-tertiary)] mt-1 font-mono">
            {wind.direction_label} {wind.direction_deg}&deg;
          </span>
        </div>

        {/* Speed & Gusts */}
        <div className="space-y-2.5">
          <div>
            <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider">Speed</div>
            <div className="text-lg font-semibold tabular-nums">{wind.speed_kmh} <span className="text-[11px] font-normal text-[var(--text-tertiary)]">km/h</span></div>
          </div>
          <div>
            <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider">Gusts</div>
            <div className="text-base font-semibold text-[var(--accent-yellow)] tabular-nums">{wind.gust_kmh} <span className="text-[11px] font-normal text-[var(--text-tertiary)]">km/h</span></div>
          </div>
          <div>
            <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider">Beaufort</div>
            <div className="text-[12px] text-[var(--text-secondary)]">{wind.beaufort_scale} — {wind.beaufort_description}</div>
          </div>
        </div>

        {/* Racing Components */}
        <div className="space-y-2.5">
          <div>
            <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider">Headwind</div>
            <div className="text-base font-semibold tabular-nums" style={{ color: wind.headwind_kmh > 0 ? "var(--accent-red)" : "var(--accent-green)" }}>
              {wind.headwind_kmh > 0 ? "+" : ""}{wind.headwind_kmh} <span className="text-[11px] font-normal text-[var(--text-tertiary)]">km/h</span>
            </div>
            <div className="text-[10px] text-[var(--text-muted)]">
              {wind.headwind_kmh > 0 ? "Opposing" : "Tailwind"}
            </div>
          </div>
          <div>
            <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider">Crosswind</div>
            <div className="text-base font-semibold text-[var(--accent-yellow)] tabular-nums">
              {wind.crosswind_kmh} <span className="text-[11px] font-normal text-[var(--text-tertiary)]">km/h</span>
            </div>
            <div className="text-[10px] text-[var(--text-muted)]">
              From {wind.crosswind_direction}
            </div>
          </div>
        </div>
      </div>

      {/* Impact details */}
      {wind.impact_details.length > 0 && (
        <div className="space-y-1 mb-3">
          {wind.impact_details.map((detail, i) => (
            <div key={i} className="text-[11px] text-[var(--text-secondary)] flex items-start gap-1.5">
              <span className="w-[3px] h-[3px] rounded-full mt-[6px] shrink-0" style={{ backgroundColor: impactColor(wind.impact_level) }} />
              {detail}
            </div>
          ))}
        </div>
      )}

      {/* Wind forecast mini-chart */}
      {windForecast.length > 0 && (
        <div className="mt-3 pt-3" style={{ borderTop: '1px solid var(--border-subtle)' }}>
          <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-[0.12em] mb-2">24h Wind Forecast</div>
          <div className="flex gap-[1px] items-end" style={{ height: "56px" }}>
            {windForecast.slice(0, 24).map((wf, i) => {
              const maxSpeed = Math.max(1, ...windForecast.map(w => w.gust_kmh));
              const barH = Math.max(4, (wf.gust_kmh / maxSpeed) * 100);
              const speedH = Math.max(2, (wf.speed_kmh / maxSpeed) * 100);
              return (
                <div key={i} className="flex-1 flex flex-col items-center justify-end h-full relative">
                  <div
                    className="w-full rounded-t-sm"
                    style={{ height: `${barH}%`, backgroundColor: "var(--accent-yellow)", opacity: 0.2 }}
                    title={`${new Date(wf.forecast_time).getHours()}:00 — Gust: ${wf.gust_kmh} km/h`}
                  />
                  <div
                    className="w-full rounded-t-sm absolute bottom-0"
                    style={{ height: `${speedH}%`, backgroundColor: "var(--brand-primary)", opacity: 0.55 }}
                    title={`Speed: ${wf.speed_kmh} km/h`}
                  />
                </div>
              );
            })}
          </div>
          <div className="flex mt-1">
            {windForecast.slice(0, 24).map((wf, i) => {
              if (i % 4 !== 0) return <div key={i} className="flex-1" />;
              return (
                <div key={i} className="flex-1 text-center text-[8px] text-[var(--text-muted)] font-mono">
                  {new Date(wf.forecast_time).getHours().toString().padStart(2, "0")}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
