function LegendItem({ color, label, count }: { color: string; label: string; count: number }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "#1e293b" }}>
      <div style={{ width: 10, height: 10, borderRadius: "50%", background: color, flexShrink: 0 }} />
      <span>
        {label} <strong>({count})</strong>
      </span>
    </div>
  );
}

export function DonutChart({
  submitted,
  total,
}: {
  submitted: number;
  total: number;
}) {
  if (total === 0) {
    return <p style={{ color: "#64748b", fontSize: 14, marginTop: 8 }}>No data yet.</p>;
  }

  const r = 40;
  const cx = 55;
  const cy = 55;
  const circumference = 2 * Math.PI * r;
  const submittedOffset = circumference * (1 - submitted / total);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 20, marginTop: 8 }}>
      <svg width="110" height="110" viewBox="0 0 110 110" style={{ flexShrink: 0 }}>
        {/* Track */}
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#e2e8f0" strokeWidth="14" />
        {/* Submitted arc */}
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="#0f766e"
          strokeWidth="14"
          strokeDasharray={circumference}
          strokeDashoffset={submittedOffset}
          transform={`rotate(-90 ${cx} ${cy})`}
        />
        {/* Center label */}
        <text
          x={cx}
          y={cy + 6}
          textAnchor="middle"
          fill="#0a3d62"
          fontSize="18"
          fontWeight="800"
        >
          {total}
        </text>
      </svg>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <LegendItem color="#0f766e" label="Submitted" count={submitted} />
      </div>
    </div>
  );
}
