"use client";

interface Props {
  confidence: number;
}

export default function ConfidenceIndicator({ confidence }: Props) {
  const color =
    confidence >= 80
      ? "var(--accent-green)"
      : confidence >= 50
        ? "var(--accent-yellow)"
        : "var(--accent-red)";

  return (
    <div className="flex items-center gap-1.5">
      <div className="flex gap-[2px]">
        {[0, 1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="rounded-[2px]"
            style={{
              width: 6,
              height: 4,
              backgroundColor:
                confidence >= (i + 1) * 20 ? color : "var(--border-color)",
              transition: 'background-color 0.2s ease',
            }}
          />
        ))}
      </div>
      <span className="text-[9px] font-medium tabular-nums" style={{ color }}>
        {confidence}%
      </span>
    </div>
  );
}
