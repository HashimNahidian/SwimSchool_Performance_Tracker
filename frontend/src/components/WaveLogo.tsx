export function WaveLogo({ size = 38, light = false }: { size?: number; light?: boolean }) {
  const stroke = light ? "rgba(255,255,255,0.9)" : "#0077b6";
  const fill = light ? "rgba(255,255,255,0.18)" : "rgba(0,119,182,0.12)";
  const dot = light ? "rgba(255,255,255,0.85)" : "#0077b6";

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Propel Swim logo"
    >
      {/* Circle background */}
      <circle cx="20" cy="20" r="19" fill={fill} stroke={stroke} strokeWidth="1.2" />

      {/* Swimmer body */}
      <circle cx="20" cy="11" r="3.2" fill={dot} />
      {/* Arms outstretched */}
      <path d="M10 17 Q15 14.5 20 16 Q25 14.5 30 17" stroke={stroke} strokeWidth="2.2" strokeLinecap="round" fill="none" />
      {/* Torso to legs */}
      <path d="M20 16 L20 24" stroke={stroke} strokeWidth="2" strokeLinecap="round" />
      {/* Kick */}
      <path d="M20 24 Q17 28 14 26" stroke={stroke} strokeWidth="2" strokeLinecap="round" fill="none" />
      <path d="M20 24 Q23 28 26 26" stroke={stroke} strokeWidth="2" strokeLinecap="round" fill="none" />

      {/* Wave below swimmer */}
      <path d="M6 31 Q10 28 14 31 Q18 34 22 31 Q26 28 34 31" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" fill="none" opacity="0.7" />
    </svg>
  );
}
