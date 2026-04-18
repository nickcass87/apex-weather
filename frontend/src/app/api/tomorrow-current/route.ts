import { NextRequest, NextResponse } from "next/server";

// Server-side only — API key never sent to browser
const TOMORROW_API_KEY = process.env.TOMORROW_API_KEY;
const REALTIME_URL = "https://api.tomorrow.io/v4/weather/realtime";
const FORECAST_URL = "https://api.tomorrow.io/v4/weather/forecast";

export async function GET(request: NextRequest) {
  const lat = request.nextUrl.searchParams.get("lat");
  const lon = request.nextUrl.searchParams.get("lon");

  if (!lat || !lon) {
    return NextResponse.json({ error: "lat and lon required" }, { status: 400 });
  }

  if (!TOMORROW_API_KEY) {
    return NextResponse.json({ error: "API key not configured" }, { status: 503 });
  }

  try {
    const [realtimeRes, forecastRes] = await Promise.all([
      fetch(`${REALTIME_URL}?location=${lat},${lon}&apikey=${TOMORROW_API_KEY}`, { cache: "no-store" }),
      fetch(`${FORECAST_URL}?location=${lat},${lon}&apikey=${TOMORROW_API_KEY}&timesteps=1h`, { cache: "no-store" }),
    ]);

    if (!realtimeRes.ok || !forecastRes.ok) {
      throw new Error(`Tomorrow.io error: ${realtimeRes.status} / ${forecastRes.status}`);
    }

    const [realtime, forecast] = await Promise.all([realtimeRes.json(), forecastRes.json()]);

    const v = realtime?.data?.values ?? {};
    const time: string = realtime?.data?.time ?? new Date().toISOString();

    function msToKmh(val: number | null | undefined): number | null {
      return val != null ? Math.round(val * 3.6 * 10) / 10 : null;
    }

    const current = {
      observed_at: time,
      temperature_c: v.temperature ?? null,
      humidity_pct: v.humidity ?? null,
      wind_speed_kmh: msToKmh(v.windSpeed),
      wind_direction_deg: v.windDirection ?? null,
      wind_gust_kmh: msToKmh(v.windGust),
      precipitation_intensity: v.rainIntensity ?? v.precipitationIntensity ?? 0,
      precipitation_probability: v.precipitationProbability ?? null,
      cloud_cover_pct: v.cloudCover ?? null,
      visibility_km: v.visibility ?? null,
      pressure_hpa: v.pressureSurfaceLevel ?? null,
      uv_index: v.uvIndex ?? null,
      dew_point_c: v.dewPoint ?? null,
      weather_code: v.weatherCode ?? null,
    };

    const hourly = (forecast?.timelines?.hourly ?? []).slice(0, 24).map((entry: { time: string; values: Record<string, number | null> }) => {
      const fv = entry.values ?? {};
      return {
        forecast_time: entry.time,
        temperature_c: fv.temperature ?? null,
        humidity_pct: fv.humidity ?? null,
        wind_speed_kmh: msToKmh(fv.windSpeed),
        wind_direction_deg: fv.windDirection ?? null,
        wind_gust_kmh: msToKmh(fv.windGust),
        precipitation_probability: fv.precipitationProbability ?? null,
        precipitation_intensity: fv.rainIntensity || fv.precipitationIntensity || 0,
        cloud_cover_pct: fv.cloudCover ?? null,
        weather_code: fv.weatherCode ?? null,
        dew_point_c: fv.dewPoint ?? null,
        pressure_hpa: fv.pressureSurfaceLevel ?? null,
      };
    });

    return NextResponse.json({ current, forecast: hourly });
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 502 });
  }
}
