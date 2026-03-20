"use client";

interface Props {
  size?: number;
  className?: string;
}

export default function ApexLogo({ size = 28, className = "" }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <defs>
        <linearGradient id="apex-grad" x1="16" y1="3" x2="16" y2="28" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#e0b65c" />
          <stop offset="100%" stopColor="#c48a30" />
        </linearGradient>
      </defs>
      {/* Racing apex "A" with warm gradient */}
      <path
        d="M16 3L4 28h5.5l2.8-6h7.4l2.8 6H28L16 3z"
        fill="url(#apex-grad)"
      />
      {/* Crossbar cutout */}
      <path
        d="M10.5 19.5h11l-1.2-2.8H11.7z"
        fill="var(--bg-primary)"
        opacity="0.9"
      />
      {/* Speed lines — warm glow */}
      <line
        x1="1.5" y1="13.5" x2="7.5" y2="13.5"
        stroke="url(#apex-grad)" strokeWidth="1.5" strokeLinecap="round" opacity="0.45"
      />
      <line
        x1="3" y1="16.5" x2="6.5" y2="16.5"
        stroke="url(#apex-grad)" strokeWidth="1" strokeLinecap="round" opacity="0.3"
      />
    </svg>
  );
}
