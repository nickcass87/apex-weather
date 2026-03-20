import { WeatherForecastPoint, TrackConditionPoint } from "@/types";

function lerpValue(a: number | null, b: number | null, t: number): number | null {
  if (a == null && b == null) return null;
  if (a == null) return b;
  if (b == null) return a;
  return a + (b - a) * t;
}

function lerpAngle(a: number, b: number, t: number): number {
  let diff = b - a;
  if (diff > 180) diff -= 360;
  if (diff < -180) diff += 360;
  return ((a + diff * t) % 360 + 360) % 360;
}

export function interpolateForecast(
  points: WeatherForecastPoint[],
  intervalMin = 10,
): WeatherForecastPoint[] {
  if (points.length < 2) return [...points];

  const result: WeatherForecastPoint[] = [];

  for (let i = 0; i < points.length - 1; i++) {
    const a = points[i];
    const b = points[i + 1];
    const aMs = new Date(a.forecast_time).getTime();
    const bMs = new Date(b.forecast_time).getTime();
    const spanMin = (bMs - aMs) / 60000;
    const steps = Math.max(1, Math.round(spanMin / intervalMin));

    for (let s = 0; s < steps; s++) {
      const t = s / steps;
      const timeMs = aMs + (bMs - aMs) * t;

      result.push({
        forecast_time: new Date(timeMs).toISOString(),
        temperature_c: lerpValue(a.temperature_c, b.temperature_c, t),
        humidity_pct: lerpValue(a.humidity_pct, b.humidity_pct, t),
        wind_speed_kmh: lerpValue(a.wind_speed_kmh, b.wind_speed_kmh, t),
        wind_direction_deg:
          a.wind_direction_deg != null && b.wind_direction_deg != null
            ? lerpAngle(a.wind_direction_deg, b.wind_direction_deg, t)
            : a.wind_direction_deg ?? b.wind_direction_deg,
        precipitation_probability: lerpValue(
          a.precipitation_probability,
          b.precipitation_probability,
          t,
        ),
        precipitation_intensity: lerpValue(
          a.precipitation_intensity,
          b.precipitation_intensity,
          t,
        ),
        cloud_cover_pct: lerpValue(a.cloud_cover_pct, b.cloud_cover_pct, t),
        weather_code: a.weather_code,
        track_temperature_c: lerpValue(
          a.track_temperature_c,
          b.track_temperature_c,
          t,
        ),
      });
    }
  }

  // Add the last point
  result.push({ ...points[points.length - 1] });
  return result;
}

export function interpolateTrackConditions(
  points: TrackConditionPoint[],
  intervalMin = 10,
): TrackConditionPoint[] {
  if (points.length < 2) return [...points];

  const result: TrackConditionPoint[] = [];

  for (let i = 0; i < points.length - 1; i++) {
    const a = points[i];
    const b = points[i + 1];
    const aMs = new Date(a.forecast_time).getTime();
    const bMs = new Date(b.forecast_time).getTime();
    const spanMin = (bMs - aMs) / 60000;
    const steps = Math.max(1, Math.round(spanMin / intervalMin));

    for (let s = 0; s < steps; s++) {
      const t = s / steps;
      const timeMs = aMs + (bMs - aMs) * t;
      const hourFrac = a.hour + (b.hour - a.hour) * t;

      result.push({
        hour: hourFrac,
        forecast_time: new Date(timeMs).toISOString(),
        condition: a.condition,
        precipitation_intensity:
          lerpValue(a.precipitation_intensity, b.precipitation_intensity, t) ?? 0,
        accumulated_rain_mm:
          lerpValue(a.accumulated_rain_mm, b.accumulated_rain_mm, t) ?? 0,
      });
    }
  }

  result.push({ ...points[points.length - 1] });
  return result;
}

export function filterByTimeRange<T extends { forecast_time: string }>(
  points: T[],
  startMs: number,
  endMs: number,
): T[] {
  return points.filter((p) => {
    const ms = new Date(p.forecast_time).getTime();
    return ms >= startMs && ms <= endMs;
  });
}

/** Compute adaptive tick interval in minutes based on visible duration */
export function getTickIntervalMin(durationMs: number): number {
  const hours = durationMs / 3600000;
  if (hours <= 6) return 30;
  if (hours <= 12) return 60;
  return 180;
}

/** Generate tick timestamps for X axis labels */
export function generateTicks(startMs: number, endMs: number): number[] {
  const intervalMin = getTickIntervalMin(endMs - startMs);
  const intervalMs = intervalMin * 60000;
  const firstTick = Math.ceil(startMs / intervalMs) * intervalMs;
  const ticks: number[] = [];
  for (let t = firstTick; t <= endMs; t += intervalMs) {
    ticks.push(t);
  }
  return ticks;
}
