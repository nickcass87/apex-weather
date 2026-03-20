"use client";

import { useState } from "react";

interface Props {
  circuitId: string | null;
}

export default function ExportButton({ circuitId }: Props) {
  const [exporting, setExporting] = useState(false);

  const handleExport = async (format: "csv" | "json") => {
    if (!circuitId) return;
    setExporting(true);
    try {
      const res = await fetch(`/api/proxy/export/forecast/${circuitId}/${format}/`);
      if (!res.ok) throw new Error("Export failed");

      if (format === "csv") {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `apex_weather_${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      } else {
        const data = await res.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `apex_weather_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch {
      // Silent fail
    } finally {
      setExporting(false);
    }
  };

  if (!circuitId) return null;

  return (
    <div className="flex items-center gap-1">
      {(["csv", "json"] as const).map((fmt) => (
        <button
          key={fmt}
          onClick={() => handleExport(fmt)}
          disabled={exporting}
          className="text-[9px] uppercase tracking-wider font-medium px-2 py-[3px] rounded transition-colors disabled:opacity-20"
          style={{
            color: 'var(--text-muted)',
            background: 'var(--bg-inset)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          {fmt}
        </button>
      ))}
    </div>
  );
}
