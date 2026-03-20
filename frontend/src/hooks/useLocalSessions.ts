"use client";

import { useState, useEffect, useCallback } from "react";
import { UserSession } from "@/types";

const STORAGE_PREFIX = "apex_sessions_";
const MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

function loadSessions(circuitId: string | null): UserSession[] {
  if (!circuitId || typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + circuitId);
    if (!raw) return [];
    const parsed: UserSession[] = JSON.parse(raw);
    // Filter out sessions older than 7 days
    const cutoff = Date.now() - MAX_AGE_MS;
    return parsed.filter(
      (s) => new Date(s.startTime).getTime() > cutoff
    ).sort((a, b) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime());
  } catch {
    return [];
  }
}

function saveSessions(circuitId: string, sessions: UserSession[]) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_PREFIX + circuitId, JSON.stringify(sessions));
  } catch {
    // Storage full or unavailable
  }
}

export function useLocalSessions(circuitId: string | null) {
  const [sessions, setSessions] = useState<UserSession[]>([]);

  useEffect(() => {
    setSessions(loadSessions(circuitId));
  }, [circuitId]);

  const addSession = useCallback(
    (name: string, startTime: string, endTime?: string) => {
      if (!circuitId) return;
      const newSession: UserSession = {
        id: crypto.randomUUID(),
        name,
        startTime,
        endTime,
        circuitId,
      };
      const updated = [...sessions, newSession].sort(
        (a, b) => new Date(a.startTime).getTime() - new Date(b.startTime).getTime()
      );
      setSessions(updated);
      saveSessions(circuitId, updated);
    },
    [circuitId, sessions]
  );

  const removeSession = useCallback(
    (id: string) => {
      if (!circuitId) return;
      const updated = sessions.filter((s) => s.id !== id);
      setSessions(updated);
      saveSessions(circuitId, updated);
    },
    [circuitId, sessions]
  );

  return { sessions, addSession, removeSession };
}
