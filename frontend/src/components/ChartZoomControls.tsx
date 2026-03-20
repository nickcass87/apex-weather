"use client";

import { ZoomLevel } from "@/types";

interface Props {
  zoomLevel: ZoomLevel;
  onZoomChange: (level: ZoomLevel) => void;
  panOffsetMs: number;
  onPanChange: (offsetMs: number) => void;
  forecastStartMs: number;
  forecastEndMs: number;
}

const ZOOM_MS: Record<ZoomLevel, number> = {
  "6h": 6 * 3600000,
  "12h": 12 * 3600000,
  "24h": 24 * 3600000,
};

const LEVELS: ZoomLevel[] = ["6h", "12h", "24h"];

export default function ChartZoomControls({
  zoomLevel,
  onZoomChange,
  panOffsetMs,
  onPanChange,
  forecastStartMs,
  forecastEndMs,
}: Props) {
  const totalMs = forecastEndMs - forecastStartMs;
  const windowMs = Math.min(ZOOM_MS[zoomLevel], totalMs);
  const maxPan = Math.max(0, totalMs - windowMs);
  const canPan = zoomLevel !== "24h" && maxPan > 0;
  const stepMs = windowMs / 2;

  const visibleLeft = totalMs > 0 ? (panOffsetMs / totalMs) * 100 : 0;
  const visibleWidth = totalMs > 0 ? (windowMs / totalMs) * 100 : 100;

  function panLeft() {
    onPanChange(Math.max(0, panOffsetMs - stepMs));
  }

  function panRight() {
    onPanChange(Math.min(maxPan, panOffsetMs + stepMs));
  }

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-1">
        {LEVELS.map((level) => (
          <button
            key={level}
            onClick={() => {
              onZoomChange(level);
              // Clamp pan when zooming out
              const newWindow = Math.min(ZOOM_MS[level], totalMs);
              const newMax = Math.max(0, totalMs - newWindow);
              if (panOffsetMs > newMax) onPanChange(newMax);
            }}
            className="px-2.5 py-1 rounded text-[10px] font-semibold tracking-wider uppercase transition-colors"
            style={{
              color:
                zoomLevel === level
                  ? "var(--brand-primary)"
                  : "var(--text-muted)",
              background:
                zoomLevel === level
                  ? "color-mix(in srgb, var(--brand-primary) 12%, transparent)"
                  : "transparent",
              border:
                zoomLevel === level
                  ? "1px solid color-mix(in srgb, var(--brand-primary) 25%, transparent)"
                  : "1px solid transparent",
            }}
          >
            {level}
          </button>
        ))}
      </div>

      {canPan && (
        <div className="flex items-center gap-1.5">
          <button
            onClick={panLeft}
            disabled={panOffsetMs <= 0}
            className="w-6 h-6 flex items-center justify-center rounded transition-opacity"
            style={{
              color: "var(--text-muted)",
              opacity: panOffsetMs <= 0 ? 0.3 : 1,
            }}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
              <path
                d="M7 1L3 5L7 9"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
          <button
            onClick={panRight}
            disabled={panOffsetMs >= maxPan}
            className="w-6 h-6 flex items-center justify-center rounded transition-opacity"
            style={{
              color: "var(--text-muted)",
              opacity: panOffsetMs >= maxPan ? 0.3 : 1,
            }}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
              <path
                d="M3 1L7 5L3 9"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
      )}

      {/* Range indicator */}
      <div
        className="flex-1 h-[3px] rounded-full relative"
        style={{ background: "var(--border-subtle)", maxWidth: "120px" }}
      >
        <div
          className="absolute top-0 h-full rounded-full"
          style={{
            left: `${visibleLeft}%`,
            width: `${visibleWidth}%`,
            background: "var(--brand-primary)",
            opacity: 0.6,
          }}
        />
      </div>
    </div>
  );
}
