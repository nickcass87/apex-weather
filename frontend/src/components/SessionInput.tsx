"use client";

import { useState } from "react";
import { UserSession } from "@/types";

interface Props {
  circuitId: string | null;
  sessions: UserSession[];
  onAdd: (name: string, startTime: string, endTime?: string) => void;
  onRemove: (id: string) => void;
}

function sessionColor(name: string): string {
  const n = name.toLowerCase();
  if (n.includes("race")) return "var(--accent-red)";
  if (n.includes("qual") || n.includes("sprint")) return "var(--accent-yellow)";
  if (n.includes("practice") || n.includes("fp")) return "var(--accent-cyan)";
  return "var(--text-secondary)";
}

export default function SessionInput({ circuitId, sessions, onAdd, onRemove }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [name, setName] = useState("");
  const [dateTime, setDateTime] = useState("");
  const [endDateTime, setEndDateTime] = useState("");

  if (!circuitId) return null;

  const handleAdd = () => {
    if (!name.trim() || !dateTime) return;
    onAdd(name.trim(), dateTime, endDateTime || undefined);
    setName("");
    setDateTime("");
    setEndDateTime("");
  };

  return (
    <div className="data-card overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3.5 py-2.5 text-left hover:bg-[var(--bg-card-hover)] transition-colors"
      >
        <span className="section-heading">Sessions</span>
        <div className="flex items-center gap-2">
          {sessions.length > 0 && (
            <span
              className="text-[9px] px-1.5 py-[2px] rounded font-semibold tabular-nums"
              style={{
                color: 'var(--brand-primary)',
                background: 'color-mix(in srgb, var(--brand-primary) 10%, transparent)',
              }}
            >
              {sessions.length}
            </span>
          )}
          <svg
            width="9"
            height="9"
            viewBox="0 0 10 10"
            fill="none"
            className={`transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
          >
            <path d="M2 3.5L5 6.5L8 3.5" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>
      </button>

      {/* Expanded */}
      {expanded && (
        <div className="px-3.5 pb-3 space-y-2" style={{ borderTop: '1px solid var(--border-subtle)' }}>
          {/* List */}
          {sessions.length > 0 && (
            <div className="space-y-1 pt-2">
              {sessions.map((s) => (
                <div
                  key={s.id}
                  className="flex items-center justify-between py-1.5 px-2 rounded-md"
                  style={{ background: 'var(--bg-inset)', border: '1px solid var(--border-subtle)' }}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="w-[5px] h-[5px] rounded-full shrink-0"
                      style={{ backgroundColor: sessionColor(s.name) }}
                    />
                    <span className="text-[11px] font-medium text-[var(--text-primary)]">{s.name}</span>
                    <span className="text-[10px] text-[var(--text-muted)] font-mono">
                      {new Date(s.startTime).toLocaleDateString([], { month: "short", day: "numeric" })}{" "}
                      {new Date(s.startTime).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      {s.endTime && `–${new Date(s.endTime).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`}
                    </span>
                  </div>
                  <button
                    onClick={() => onRemove(s.id)}
                    className="text-[var(--text-muted)] hover:text-[var(--accent-red)] transition-colors p-0.5"
                    title="Remove"
                  >
                    <svg width="8" height="8" viewBox="0 0 10 10" fill="none">
                      <path d="M2 2L8 8M8 2L2 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Add form */}
          <div className="space-y-1.5 pt-1">
            <div className="flex gap-1.5 items-end">
              <div className="flex-1">
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Session name…"
                  className="w-full px-2 py-1.5 rounded-md text-[11px] text-[var(--text-primary)] placeholder:text-[var(--text-muted)]"
                  style={{
                    background: 'var(--bg-inset)',
                    border: '1px solid var(--border-color)',
                  }}
                />
              </div>
              <div>
                <label className="text-[8px] text-[var(--text-muted)] uppercase">Start</label>
                <input
                  type="datetime-local"
                  value={dateTime}
                  onChange={(e) => setDateTime(e.target.value)}
                  className="px-2 py-1.5 rounded-md text-[11px] text-[var(--text-primary)]"
                  style={{
                    background: 'var(--bg-inset)',
                    border: '1px solid var(--border-color)',
                  }}
                />
              </div>
              <div>
                <label className="text-[8px] text-[var(--text-muted)] uppercase">End</label>
                <input
                  type="datetime-local"
                  value={endDateTime}
                  onChange={(e) => setEndDateTime(e.target.value)}
                  className="px-2 py-1.5 rounded-md text-[11px] text-[var(--text-primary)]"
                  style={{
                    background: 'var(--bg-inset)',
                    border: '1px solid var(--border-color)',
                  }}
                />
              </div>
              <button
                onClick={handleAdd}
                disabled={!name.trim() || !dateTime}
                className="px-2.5 py-1.5 rounded-md text-[11px] font-medium transition-opacity disabled:opacity-20"
                style={{
                  background: 'var(--brand-primary)',
                  color: 'var(--bg-primary)',
                }}
              >
                Add
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
