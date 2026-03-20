"use client";

import { Circuit } from "@/types";

interface Props {
  circuits: Circuit[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export default function CircuitSelector({ circuits, selectedId, onSelect }: Props) {
  const grouped = circuits.reduce<Record<string, Circuit[]>>((acc, c) => {
    (acc[c.country] = acc[c.country] || []).push(c);
    return acc;
  }, {});

  const countries = Object.keys(grouped).sort();

  return (
    <div className="relative">
      <select
        value={selectedId || ""}
        onChange={(e) => onSelect(e.target.value)}
        className="w-full appearance-none cursor-pointer transition-colors duration-150"
        style={{
          padding: '6px 32px 6px 11px',
          fontSize: '13px',
          fontWeight: 500,
          fontFamily: 'inherit',
          letterSpacing: '0.01em',
          color: 'var(--text-primary)',
          background: 'var(--bg-inset)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          boxShadow: 'var(--shadow-card)',
          backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%235e5852' fill='none' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`,
          backgroundRepeat: 'no-repeat',
          backgroundPosition: 'right 12px center',
        }}
      >
        <option value="" disabled>
          Select circuit…
        </option>
        {countries.map((country) => (
          <optgroup key={country} label={country}>
            {grouped[country].map((circuit) => (
              <option key={circuit.id} value={circuit.id}>
                {circuit.name}
                {circuit.series ? ` · ${circuit.series}` : ""}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </div>
  );
}
