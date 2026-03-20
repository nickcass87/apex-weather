import { UserSession } from "@/types";

export function sessionShortName(name: string): string {
  const n = name.toLowerCase();
  if (n === "qual group a") return "QA";
  if (n === "qual group b") return "QB";
  if (n === "semi finals") return "SF";
  if (n.startsWith("fp")) return name.toUpperCase();
  if (n === "race") return "RACE";
  if (name.length > 6) return name.slice(0, 4).toUpperCase();
  return name.toUpperCase();
}

export function sessionColor(name: string): string {
  const n = name.toLowerCase();
  if (n.includes("race")) return "var(--accent-red)";
  if (n.includes("qual") || n.includes("sprint") || n.includes("semi")) return "var(--accent-yellow)";
  if (n.includes("practice") || n.includes("fp")) return "var(--accent-cyan)";
  return "var(--text-secondary)";
}

/**
 * For a session, compute its fractional position within a time range [rangeStart, rangeEnd].
 * Returns { left, width } as percentages (0-100), or null if the session doesn't overlap.
 */
export function sessionOverlap(
  session: UserSession,
  rangeStartMs: number,
  rangeEndMs: number,
): { left: number; width: number; name: string; shortName: string; color: string } | null {
  const sStart = new Date(session.startTime).getTime();
  // Default to 40 min if no endTime
  const sEnd = session.endTime
    ? new Date(session.endTime).getTime()
    : sStart + 40 * 60 * 1000;

  // Check overlap
  if (sEnd <= rangeStartMs || sStart >= rangeEndMs) return null;

  const rangeMs = rangeEndMs - rangeStartMs;
  if (rangeMs <= 0) return null;

  const clampedStart = Math.max(sStart, rangeStartMs);
  const clampedEnd = Math.min(sEnd, rangeEndMs);

  const left = ((clampedStart - rangeStartMs) / rangeMs) * 100;
  const width = ((clampedEnd - clampedStart) / rangeMs) * 100;

  return { left, width, name: session.name, shortName: sessionShortName(session.name), color: sessionColor(session.name) };
}
