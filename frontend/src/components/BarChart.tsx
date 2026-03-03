export function BarChart({
  data,
  labelWidth = 130,
}: {
  data: { label: string; value: number; color?: string }[];
  labelWidth?: number;
}) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {data.map(({ label, value, color }) => (
        <div key={label} className="skill-bar-row">
          <span className="skill-bar-label" style={{ minWidth: labelWidth }}>{label}</span>
          <div className="skill-bar-track">
            <div
              className="skill-bar-fill"
              style={{ width: `${(value / max) * 100}%`, background: color ?? "#0077b6" }}
            />
          </div>
          <span className="skill-bar-count">{value}</span>
        </div>
      ))}
    </div>
  );
}
