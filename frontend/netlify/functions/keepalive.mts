/**
 * Netlify scheduled function — runs every 10 minutes to keep the Render
 * free-tier backend alive and prevent the 30-60s cold-start delay.
 *
 * Schedule: "* /10 * * * *" (every 10 minutes)
 */

const RENDER_HEALTH_URL = "https://apex-weather-api.onrender.com/health";

export default async function handler(): Promise<Response> {
  const start = Date.now();
  try {
    const res = await fetch(RENDER_HEALTH_URL, {
      method: "GET",
      headers: { "User-Agent": "netlify-keepalive/1.0" },
    });
    const elapsed = Date.now() - start;
    const body = await res.text();
    console.log(`[keepalive] status=${res.status} elapsed=${elapsed}ms body=${body}`);
    return new Response(`OK status=${res.status} elapsed=${elapsed}ms`, { status: 200 });
  } catch (err) {
    const elapsed = Date.now() - start;
    console.error(`[keepalive] error after ${elapsed}ms:`, err);
    return new Response(`ERROR: ${String(err)}`, { status: 500 });
  }
}

export const config = {
  schedule: "*/10 * * * *",
};
