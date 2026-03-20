"use client";

import { useState, useEffect, useCallback } from "react";
import { WindForecastPoint } from "@/types";

interface Props {
  windForecast: WindForecastPoint[];
  selectedIndex: number;
  onIndexChange: (index: number) => void;
}

export default function TimeSlider({
  windForecast,
  selectedIndex,
  onIndexChange,
}: Props) {
  const [playing, setPlaying] = useState(false);
  const count = windForecast.length;

  useEffect(() => {
    if (!playing || count === 0) return;
    const id = setInterval(() => {
      onIndexChange(selectedIndex >= count - 1 ? 0 : selectedIndex + 1);
    }, 800);
    return () => clearInterval(id);
  }, [playing, selectedIndex, count, onIndexChange]);

  const handlePlay = useCallback(() => {
    setPlaying((p) => !p);
  }, []);

  if (count === 0) return null;

  const currentPoint = windForecast[selectedIndex];
  const timeLabel = currentPoint
    ? new Date(currentPoint.forecast_time).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";

  const firstTime = windForecast[0]
    ? new Date(windForecast[0].forecast_time).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";

  const lastTime = windForecast[count - 1]
    ? new Date(windForecast[count - 1].forecast_time).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";

  const pct = (selectedIndex / Math.max(count - 1, 1)) * 100;

  return (
    <div
      className="flex items-center gap-3 px-3 py-2"
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        borderRadius: '10px',
        boxShadow: 'var(--shadow-card)',
      }}
    >
      {/* Play/Pause */}
      <button
        onClick={handlePlay}
        className="shrink-0 flex items-center justify-center transition-all duration-150"
        title={playing ? "Pause" : "Play through forecast"}
        style={{
          width: 28,
          height: 28,
          borderRadius: '50%',
          background: 'var(--brand-primary)',
          color: 'var(--bg-primary)',
          boxShadow: '0 0 10px rgba(212,160,74,0.25)',
        }}
      >
        {playing ? (
          <svg width="10" height="10" viewBox="0 0 12 12" fill="currentColor">
            <rect x="1.5" y="1.5" width="3" height="9" rx="0.5" />
            <rect x="7.5" y="1.5" width="3" height="9" rx="0.5" />
          </svg>
        ) : (
          <svg width="10" height="10" viewBox="0 0 12 12" fill="currentColor">
            <polygon points="3,0.5 11.5,6 3,11.5" />
          </svg>
        )}
      </button>

      {/* Start time */}
      <span className="text-[11px] text-[var(--text-tertiary)] w-10 shrink-0 text-center font-mono">
        {firstTime}
      </span>

      {/* Slider */}
      <div className="flex-1 relative" style={{ minHeight: "28px" }}>
        <input
          type="range"
          min={0}
          max={count - 1}
          value={selectedIndex}
          onChange={(e) => {
            setPlaying(false);
            onIndexChange(Number(e.target.value));
          }}
          className="w-full cursor-pointer"
          style={{
            background: `linear-gradient(to right, var(--brand-primary) ${pct}%, var(--border-color) ${pct}%)`,
          }}
        />
        {/* Hour ticks */}
        {windForecast.map((wf, i) => {
          if (i % 3 !== 0 && count > 12) return null;
          const hr = new Date(wf.forecast_time).getHours();
          return (
            <span
              key={i}
              className="text-[7px] text-[var(--text-muted)]"
              style={{
                position: "absolute",
                left: `${(i / Math.max(count - 1, 1)) * 100}%`,
                transform: "translateX(-50%)",
                top: "17px",
              }}
            >
              {hr.toString().padStart(2, "0")}
            </span>
          );
        })}
      </div>

      {/* End time */}
      <span className="text-[11px] text-[var(--text-tertiary)] w-10 shrink-0 text-center font-mono">
        {lastTime}
      </span>

      {/* Current time */}
      <div className="flex flex-col items-center shrink-0 min-w-[60px]">
        <span className="text-[13px] font-semibold tabular-nums" style={{ color: 'var(--brand-highlight)' }}>
          {timeLabel}
        </span>
        <span className="text-[8px] text-[var(--text-muted)] uppercase tracking-[0.12em]">
          {selectedIndex === 0 ? "Now" : `+${selectedIndex}h`}
        </span>
      </div>

      {/* Wind readout */}
      <div
        className="flex items-center gap-2 shrink-0 pl-2.5"
        style={{ borderLeft: '1px solid var(--border-subtle)' }}
      >
        <div className="text-center">
          <div className="text-[8px] text-[var(--text-muted)] uppercase tracking-wider">Wind</div>
          <div className="text-[12px] font-semibold tabular-nums">{currentPoint?.speed_kmh ?? 0} <span className="text-[9px] font-normal text-[var(--text-tertiary)]">km/h</span></div>
        </div>
        <div className="text-center">
          <div className="text-[8px] text-[var(--text-muted)] uppercase tracking-wider">Dir</div>
          <div className="text-[12px] font-semibold">{currentPoint?.direction_label ?? "N"}</div>
        </div>
      </div>

      {/* Precipitation readout */}
      {(() => {
        const intensity = currentPoint?.precipitation_intensity ?? 0;
        const prob = currentPoint?.precipitation_probability ?? 0;
        const condition = currentPoint?.track_condition ?? "dry";
        const hasRain = intensity >= 0.05;
        const color = hasRain
          ? intensity >= 7.5 ? "#bf5858"
          : intensity >= 2.5 ? "#d9af42"
          : intensity >= 0.5 ? "#5a9dba"
          : "#5aacb8"
          : condition !== "dry" ? "#5aacb8" : "var(--text-muted)";
        const label = hasRain
          ? intensity >= 7.5 ? "HEAVY"
          : intensity >= 2.5 ? "MOD"
          : intensity >= 0.5 ? "LIGHT"
          : "DRIZZLE"
          : condition !== "dry" ? condition.replace("_", " ").toUpperCase() : "DRY";

        return (
          <div
            className="flex items-center gap-2 shrink-0 pl-2.5"
            style={{ borderLeft: '1px solid var(--border-subtle)' }}
          >
            <div className="text-center">
              <div className="text-[8px] text-[var(--text-muted)] uppercase tracking-wider">Rain</div>
              <div className="text-[12px] font-semibold tabular-nums" style={{ color }}>
                {hasRain ? intensity.toFixed(1) : "0.0"} <span className="text-[9px] font-normal text-[var(--text-tertiary)]">mm/h</span>
              </div>
            </div>
            <div className="text-center">
              <div className="text-[8px] text-[var(--text-muted)] uppercase tracking-wider">Track</div>
              <div className="text-[10px] font-semibold" style={{ color }}>{label}</div>
            </div>
            {prob > 0 && (
              <div className="text-center">
                <div className="text-[8px] text-[var(--text-muted)] uppercase tracking-wider">Prob</div>
                <div className="text-[12px] font-semibold tabular-nums">{prob}<span className="text-[9px] font-normal text-[var(--text-tertiary)]">%</span></div>
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
}
