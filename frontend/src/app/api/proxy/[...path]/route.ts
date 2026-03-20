import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const targetPath = path.join("/");
  // Ensure trailing slash to match FastAPI router expectations
  const url = `${BACKEND_URL}/api/v1/${targetPath}${targetPath.endsWith("/") ? "" : "/"}`;

  try {
    const res = await fetch(url, { cache: "no-store", redirect: "follow" });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      { error: `Backend unreachable at ${url}` },
      { status: 502 }
    );
  }
}
