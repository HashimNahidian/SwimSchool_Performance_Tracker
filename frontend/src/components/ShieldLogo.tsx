export function ShieldLogo({
  size = 64,
  color = "#1a4080",
}: {
  size?: number;
  color?: string;
}) {
  const h = Math.round(size * 1.12);
  return (
    <svg
      width={size}
      height={h}
      viewBox="0 0 100 112"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Outer shield body */}
      <path
        d="M50 4 L88 17 Q93 22 93 36 L93 65 Q91 90 50 108 Q9 90 7 65 L7 36 Q7 22 12 17 Z"
        fill={color}
      />
      {/* Inner shield outline */}
      <path
        d="M50 16 L80 27 Q84 31 84 43 L84 65 Q82 83 50 97 Q18 83 16 65 L16 43 Q16 31 20 27 Z"
        fill="none"
        stroke="white"
        strokeWidth="1.8"
        strokeOpacity="0.6"
      />
      {/* Left PCB circuit traces */}
      <circle cx="19" cy="54" r="2.8" fill="white" fillOpacity="0.85" />
      <circle cx="19" cy="64" r="2.8" fill="white" fillOpacity="0.85" />
      <line x1="21.8" y1="54" x2="32" y2="54" stroke="white" strokeWidth="1.5" strokeOpacity="0.85" />
      <line x1="21.8" y1="64" x2="32" y2="64" stroke="white" strokeWidth="1.5" strokeOpacity="0.85" />
      <line x1="32" y1="54" x2="32" y2="64" stroke="white" strokeWidth="1.5" strokeOpacity="0.85" />
      {/* Right PCB circuit traces */}
      <circle cx="81" cy="54" r="2.8" fill="white" fillOpacity="0.85" />
      <circle cx="81" cy="64" r="2.8" fill="white" fillOpacity="0.85" />
      <line x1="78.2" y1="54" x2="68" y2="54" stroke="white" strokeWidth="1.5" strokeOpacity="0.85" />
      <line x1="78.2" y1="64" x2="68" y2="64" stroke="white" strokeWidth="1.5" strokeOpacity="0.85" />
      <line x1="68" y1="54" x2="68" y2="64" stroke="white" strokeWidth="1.5" strokeOpacity="0.85" />
      {/* The "5" */}
      <text
        x="50"
        y="84"
        textAnchor="middle"
        fill="white"
        fontSize="44"
        fontWeight="900"
        fontFamily="'Segoe UI', 'Arial Black', Arial, sans-serif"
      >
        5
      </text>
    </svg>
  );
}
