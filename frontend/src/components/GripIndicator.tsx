"use client";

import { GripEstimate } from "@/types";

interface Props {
  grip: GripEstimate;
}

function gripColor(pct: number): string {
  if (pct >= 80) return "var(--accent-green)";
  if (pct >= 60) return "var(--accent-yellow)";
  return "var(--accent-red)";
}

export default function GripIndicator({ grip }: Props) {
  return (
    <div className="data-card p-4">
      <h3 className="section-heading mb-3">Grip Level</h3>

      <div className="flex items-center gap-4 mb-3">
        {/* Ring gauge */}
        <div className="relative w-16 h-16 shrink-0">
          <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
            <circle cx="50" cy="50" r="42" fill="none" stroke="var(--border-color)" strokeWidth="6" />
            <circle
              cx="50" cy="50" r="42"
              fill="none"
              stroke={gripColor(grip.grip_pct)}
              strokeWidth="6"
              strokeDasharray={`${(grip.grip_pct / 100) * 264} 264`}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-[15px] font-semibold tabular-nums" style={{ color: gripColor(grip.grip_pct) }}>
              {grip.grip_pct.toFixed(0)}%
            </span>
          </div>
        </div>

        {/* Breakdown bars */}
        <div className="flex-1 space-y-2">
          <div>
            <div className="flex items-center justify-between text-[9px] text-[var(--text-muted)] uppercase tracking-wider mb-1">
              <span>Mechanical</span>
              <span className="tabular-nums">{grip.mechanical_grip_pct.toFixed(0)}%</span>
            </div>
            <div className="h-[4px] rounded-full bg-[var(--bg-inset)]">
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{
                  width: `${grip.mechanical_grip_pct}%`,
                  backgroundColor: gripColor(grip.mechanical_grip_pct),
                }}
              />
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between text-[9px] text-[var(--text-muted)] uppercase tracking-wider mb-1">
              <span>Aero Efficiency</span>
              <span className="tabular-nums">{grip.aero_efficiency_pct.toFixed(0)}%</span>
            </div>
            <div className="h-[4px] rounded-full bg-[var(--bg-inset)]">
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{
                  width: `${grip.aero_efficiency_pct}%`,
                  backgroundColor: gripColor(grip.aero_efficiency_pct),
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Factors */}
      {Object.entries(grip.factors).length > 0 && (
        <div className="space-y-1 pt-2" style={{ borderTop: '1px solid var(--border-subtle)' }}>
          {Object.entries(grip.factors).map(([key, value]) => (
            <div key={key} className="flex items-start gap-1.5 text-[11px] text-[var(--text-secondary)]">
              <span className="w-[3px] h-[3px] rounded-full bg-[var(--brand-primary)] mt-[6px] shrink-0 opacity-50" />
              <span className="capitalize">{value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
