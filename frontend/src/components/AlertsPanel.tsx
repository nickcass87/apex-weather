"use client";

import { Alert } from "@/types";

interface Props {
  alerts: Alert[];
}

const severityColor: Record<string, string> = {
  critical: "var(--accent-red)",
  warning: "var(--accent-yellow)",
  info: "var(--accent-blue)",
};

export default function AlertsPanel({ alerts }: Props) {
  if (alerts.length === 0) {
    return (
      <div className="data-card p-3 text-center">
        <span className="text-[11px] text-[var(--text-muted)]">No active alerts</span>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      <h3 className="section-heading px-0.5">Alerts</h3>
      {alerts.map((alert) => {
        const color = severityColor[alert.severity] || severityColor.info;
        return (
          <div
            key={alert.id}
            className="data-card p-2.5"
            style={{ borderLeft: `3px solid ${color}` }}
          >
            <div className="flex items-start gap-2">
              <span
                className="text-[9px] font-semibold uppercase shrink-0 px-1.5 py-[2px] rounded tracking-wider"
                style={{
                  color,
                  background: `color-mix(in srgb, ${color} 12%, transparent)`,
                }}
              >
                {alert.alert_type}
              </span>
              <p className="text-[12px] text-[var(--text-secondary)] leading-snug">{alert.message}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
