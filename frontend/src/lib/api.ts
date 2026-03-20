import { Circuit, WeatherResponse } from "@/types";

// Use Next.js API route proxy to reach the backend server-side
const API_BASE = "/api/proxy";

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
