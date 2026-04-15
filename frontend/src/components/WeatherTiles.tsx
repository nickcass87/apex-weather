"use client";

import { WeatherCurrent } from "@/types";

interface Props {
  weather: WeatherCurrent;
}

function windDirectionLabel(deg: number | null): string {
  if (deg === null) return "--";
  const dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  return dirs[Math.round(deg / 45) % 8];
}

function rainEtaDisplay(minutes: number | null, intensity: number | null): string {
  if (minutes === null) return "No rain";
  if (minutes <= 0) {
    // Distinguish "raining now" from "rain arriving in <1 min"
    if (intensity !== null && intensity >= 0.05) return "Raining Now";
    return "Imminent";
  }
  if (minutes < 60) return `${Math.round(minutes)} min`;
  const hours = Math.floor(minutes / 60);
  const mins = Math.round(minutes % 60);
  return `${hours}h ${mins}m`;
}

function pressureTrendArrow(trend: string | null): string {
  if (trend === "rising") return "↑";
  if (trend === "falling") return "↓";
  return "→";
}

function pressureTrendColor(trend: string | null): string {
  if (trend === "rising") return "var(--accent-green)";
  if (trend === "falling") return "var(--accent-red)";
  return "var(--text-primary)";
}

function Tile({
  label,
  value,
  unit,
  accentColor,
}: {
  label: string;
  value: string;
  unit?: string;
  accentColor?: string;
}) {
  return (
    <div
      className="data-card p-3.5"
      style={accentColor ? {
        borderTop: `2px solid color-mix(in srgb, ${accentColor} 40%, transparent)`,
      } : undefined}
    >
      <div className="text-[9px] uppercase tracking-[0.12em] font-semibold text-[var(--text-muted)] mb-2">
        {label}
      </div>
      <div
        className="text-[22px] font-semibold tabular-nums leading-none"
        style={{ color: accentColor || 'var(--text-primary)' }}
      >
        {value}
        {unit && (
          <span className="text-[11px] ml-1 font-normal text-[var(--text-tertiary)]">{unit}</span>
        )}
      </div>
    </div>
  );
}

export default function WeatherTiles({ weather }: Props) {
  const rainColor =
    weather.rain_eta_minutes !== null && weather.rain_eta_minutes < 30
      ? "var(--accent-red)"
      : weather.rain_eta_minutes !== null
        ? "var(--accent-yellow)"
        : "var(--accent-green)";

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <Tile
        label="Rain ETA"
        value={rainEtaDisplay(weather.rain_eta_minutes, weather.precipitation_intensity)}
        accentColor={rainColor}
      />
      <Tile
        label="Track Temp"
        value={weather.track_temperature_c?.toFixed(1) ?? "--"}
        unit="°C"
        accentColor="var(--accent-yellow)"
      />
      <Tile
        label="Air Temp"
        value={weather.temperature_c?.toFixed(1) ?? "--"}
        unit="°C"
      />
      <Tile
        label="Wind"
        value={`${weather.wind_speed_kmh?.toFixed(0) ?? "--"}`}
        unit={`km/h ${windDirectionLabel(weather.wind_direction_deg)}`}
      />
      <Tile
        label="Humidity"
        value={weather.humidity_pct?.toFixed(0) ?? "--"}
        unit="%"
      />
      <Tile
        label={(weather.precipitation_intensity ?? 0) >= 0.05 ? "Rain Intensity" : "Rain Prob"}
        value={
          (weather.precipitation_intensity ?? 0) >= 0.05
            ? (weather.precipitation_intensity?.toFixed(1) ?? "--")
            : (weather.precipitation_probability?.toFixed(0) ?? "--")
        }
        unit={(weather.precipitation_intensity ?? 0) >= 0.05 ? "mm/hr" : "%"}
        accentColor={
          (weather.precipitation_intensity ?? 0) >= 0.05
            ? "var(--accent-red)"
            : (weather.precipitation_probability ?? 0) > 60
              ? "var(--accent-red)"
              : undefined
        }
      />
      <Tile
        label="Cloud Cover"
        value={weather.cloud_cover_pct?.toFixed(0) ?? "--"}
        unit="%"
      />
      <Tile
        label="Pressure"
        value={`${weather.pressure_hpa?.toFixed(0) ?? "--"} ${pressureTrendArrow(weather.pressure_trend ?? null)}`}
        unit="hPa"
        accentColor={weather.pressure_trend !== "steady" && weather.pressure_trend != null ? pressureTrendColor(weather.pressure_trend) : undefined}
      />
      <Tile
        label="Wet Bulb"
        value={weather.wet_bulb_c?.toFixed(1) ?? "--"}
        unit="°C"
        accentColor="var(--accent-blue)"
      />
      <Tile
        label="Dew Spread"
        value={weather.dew_point_spread_c?.toFixed(1) ?? "--"}
        unit="°C"
        accentColor={(weather.dew_point_spread_c ?? 99) < 3 ? "var(--accent-red)" : undefined}
      />
    </div>
  );
}
