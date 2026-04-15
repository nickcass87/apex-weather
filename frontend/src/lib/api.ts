import { Circuit, WeatherResponse, ModelComparisonResponse, NowcastResponse, CalibrationStats } from "@/types";

// Route all API calls through the Next.js proxy to avoid CORS issues.
// The proxy forwards to NEXT_PUBLIC_API_URL server-side.
const PROXY_BASE = "/api/proxy";

async function fetchApi<T>(path: string): Promise<T> {
  // Strip leading slash for proxy path construction
  const cleanPath = path.startsWith("/") ? path.slice(1) : path;
  const res = await fetch(`${PROXY_BASE}/${cleanPath}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function getCircuits(): Promise<Circuit[]> {
  return fetchApi<Circuit[]>("/circuits/");
}

export async function getCircuit(id: string): Promise<Circuit> {
  return fetchApi<Circuit>(`/circuits/${id}`);
}

export async function getWeather(circuitId: string): Promise<WeatherResponse> {
  return fetchApi<WeatherResponse>(`/weather/${circuitId}`);
}

export async function getModelComparison(circuitId: string): Promise<ModelComparisonResponse> {
  return fetchApi<ModelComparisonResponse>(`/weather/${circuitId}/models`);
}

export async function getNowcast(circuitId: string): Promise<NowcastResponse> {
  return fetchApi<NowcastResponse>(`/weather/${circuitId}/nowcast`);
}

export async function getCalibration(circuitId: string): Promise<CalibrationStats> {
  return fetchApi<CalibrationStats>(`/weather/${circuitId}/calibration`);
}
