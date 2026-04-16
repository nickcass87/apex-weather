import { NextRequest, NextResponse } from "next/server";

// Use server-only env var (no NEXT_PUBLIC_ prefix) so the backend URL is never exposed to the browser
const BACKEND_URL = process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// How long to wait for a single attempt (covers Render cold-start ~30-60s)
const REQUEST_TIMEOUT_MS = 55_000;
// How long to pause before retrying after a cold-start failure
const RETRY_DELAY_MS = 3_000;

/** Fetch with an explicit AbortController timeout. */
async function fetchWithTimeout(url: string): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(url, {
      cache: "no-store",
      redirect: "follow",
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }
}

/** Returns true when the status indicates a transient server/gateway error worth retrying. */
function isRetryableStatus(status: number): boolean {
  return status === 502 || status === 503 || status === 504;
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const targetPath = path.join("/");
  // Ensure trailing slash to match FastAPI router expectations
  const url = `${BACKEND_URL}/api/v1/${targetPath}${targetPath.endsWith("/") ? "" : "/"}`;

  // --- First attempt ---
  try {
    const res = await fetchWithTimeout(url);
    if (!isRetryableStatus(res.status)) {
      const data = await res.json();
      return NextResponse.json(data, { status: res.status });
    }
    // 502/503/504 — Render cold start likely. Fall through to retry.
  } catch {
    // Network error or timeout — fall through to retry
  }

  // --- Retry after short delay (gives Render time to finish waking up) ---
  await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
  try {
    const retryRes = await fetchWithTimeout(url);
    const data = await retryRes.json();
    return NextResponse.json(data, { status: retryRes.status });
  } catch {
    return NextResponse.json(
      { error: `Backend unreachable at ${url}` },
      { status: 502 }
    );
  }
}
