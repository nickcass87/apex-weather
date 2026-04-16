"use client";

import { CalibrationStats } from "@/types";

interface Props {
  calibration: CalibrationStats;
}

function skillColor(score: number): string {
  if (score >= 70) return "var(--accent-green)";
  if (score >= 40) return "var(--accent-yellow)";
  return "var(--accent-red)";
}

function BiasArrow({ value, threshold = 0.3 }: { value: number; threshold?: number }) {
  if (Math.abs(value) < threshold) {
    return <span className="text-[var(--text-muted)]">→</span>;
  }
  return (
    <span style={{ color: value > 0 ? "var(--accent-red)" : "var(--accent-green)" }}>
      {value > 0 ? "↑" : "↓"}
    </span>
  );
}

function MetricRow({
  label,
  biasValue,
  biasFormatted,
  mae,
  maeUnit,
  arrowThreshold,
}: {
  label: string;
  biasValue: number;
  biasFormatted: string;
  mae: number;
  maeUnit: string;
  arrowThreshold?: number;
}) {
  return (
    <div
      className="flex items-center justify-between py-2"
      style={{ borderBottom: "1px solid var(--border-subtle)" }}
    >
      <div className="flex items-center gap-2">
        <span className="text-[9px] uppercase tracking-[0.12em] font-semibold text-[var(--text-muted)] w-24">
          {label}
        </span>
        <BiasArrow value={biasValue} threshold={arrowThreshold} />
      </div>
      <div className="flex items-center gap-4">
        <span
          className="text-[12px] font-semibold tabular-nums font-mono"
          style={{ color: Math.abs(biasValue) < (arrowThreshold ?? 0.3) ? "var(--text-secondary)" : "var(--text-primary)" }}
        >
          {biasFormatted}
        </span>
        <span className="text-[10px] text-[var(--text-muted)] tabular-nums w-20 text-right">
          MAE {mae.toFixed(2)} {maeUnit}
        </span>
      </div>
    </div>
  );
}

export default function CalibrationPanel({ calibration }: Props) {
  if (!calibration.is_available) {
    return (
      <div className="data-card p-4">
        <h3 className="section-heading mb-2">Forecast Calibration</h3>
        <p className="text-[11px] text-[var(--text-muted)]">
          Calibration data unavailable — ERA5 archive access required.
        </p>
      </div>
    );
  }

  const computedDate = new Date(calibration.computed_at);
  const ageHours = Math.round((Date.now() - computedDate.getTime()) / 3600000);

  const tempBiasFormatted = `${calibration.temp_bias_c >= 0 ? "+" : ""}${calibration.temp_bias_c.toFixed(1)}°C`;
  const precipFormatted = `×${calibration.precip_ratio.toFixed(2)}`;
  const windBiasFormatted = `${calibration.wind_bias_kmh >= 0 ? "+" : ""}${calibration.wind_bias_kmh.toFixed(1)} km/h`;

  // Precipitation bias value for arrow direction (ratio > 1 means over-prediction)
  const precipBiasDirection = calibration.precip_ratio - 1.0;

  return (
    <div className="data-card p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="section-heading">Forecast Calibration</h3>
          <p className="text-[9px] text-[var(--text-muted)] mt-0.5">
            ECMWF IFS vs ERA5 · {calibration.backtest_days}d backtest · {calibration.sample_count.toLocaleString()} hourly pairs
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="text-[20px] font-bold tabular-nums leading-none"
            style={{ color: skillColor(calibration.skill_score) }}
          >
            {calibration.skill_score}
          </span>
          <div>
            <div className="text-[8px] text-[var(--text-muted)] uppercase tracking-wider">Skill</div>
            <div className="text-[8px] text-[var(--text-muted)] uppercase tracking-wider">Score</div>
          </div>
        </div>
      </div>

      {/* Correction summary pill */}
      <div
        className="text-[10px] font-mono px-3 py-1.5 rounded mb-3 inline-block"
        style={{
          background: "var(--bg-inset)",
          border: "1px solid var(--border-color)",
          color: "var(--text-secondary)",
        }}
      >
        Applied: {calibration.correction_summary}
      </div>

      {/* Metric rows */}
      <div>
        <MetricRow
          label="Temperature"
          biasValue={calibration.temp_bias_c}
          biasFormatted={tempBiasFormatted}
          mae={calibration.temp_mae_c}
          maeUnit="°C"
          arrowThreshold={0.3}
        />
        <MetricRow
          label="Precipitation"
          biasValue={precipBiasDirection}
          biasFormatted={precipFormatted}
          mae={calibration.precip_mae_mmhr}
          maeUnit="mm/hr"
          arrowThreshold={0.05}
        />
        <MetricRow
          label="Wind Speed"
          biasValue={calibration.wind_bias_kmh}
          biasFormatted={windBiasFormatted}
          mae={calibration.wind_mae_kmh}
          maeUnit="km/h"
          arrowThreshold={0.5}
        />
      </div>

      <div className="flex items-center justify-between mt-3 pt-2" style={{ borderTop: "1px solid var(--border-subtle)" }}>
        <div className="text-[8px] text-[var(--text-muted)]">
          <span
            className="inline-block w-[5px] h-[5px] rounded-full mr-1"
            style={{ backgroundColor: skillColor(calibration.skill_score) }}
          />
          {calibration.skill_score >= 70 ? "High skill" : calibration.skill_score >= 40 ? "Moderate skill" : "Low skill"} · corrections auto-applied to forecast
        </div>
        <span className="text-[8px] text-[var(--text-muted)] font-mono">
          {ageHours < 1 ? "just now" : `${ageHours}h ago`}
        </span>
      </div>
    </div>
  );
}
