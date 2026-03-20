import { Circuit, WeatherResponse } from "@/types";

// Call backend directly — NEXT_PUBLIC_API_URL is inlined at build time
const BACKEND =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_BASE = `${BACKEND}/api/v1`;

async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
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
