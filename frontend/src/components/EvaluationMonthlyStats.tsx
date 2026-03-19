import type { EvaluationSummary } from "../types";

export function currentMonthStats(rows: EvaluationSummary[]) {
  const now = new Date();
  const month = now.getMonth();
  const year = now.getFullYear();
  const currentMonthRows = rows.filter((row) => {
    const createdAt = new Date(row.created_at);
    return createdAt.getMonth() === month && createdAt.getFullYear() === year;
  });
  const instructors = new Set(currentMonthRows.map((row) => row.instructor_id));

  return {
    total: currentMonthRows.length,
    instructorCount: instructors.size,
    flaggedCount: currentMonthRows.filter((row) => row.needs_reevaluation).length,
  };
}

export function EvaluationMonthlyStats({
  rows,
  flaggedLabel = "Evaluations needing reevaluation",
  flaggedActive = false,
  onFlaggedClick,
}: {
  rows: EvaluationSummary[];
  flaggedLabel?: string;
  flaggedActive?: boolean;
  onFlaggedClick?: () => void;
}) {
  const stats = currentMonthStats(rows);
  const flaggedCardProps = onFlaggedClick
    ? {
        as: "button" as const,
        type: "button" as const,
        onClick: onFlaggedClick,
      }
    : null;

  return (
    <div className="stat-cards supervisor-stat-cards">
      <div className="stat-card">
        <div className="stat-card-value" style={{ color: "#023e8a" }}>{stats.total}</div>
        <div className="stat-card-label">Total Evaluations this month</div>
      </div>
      <div className="stat-card">
        <div className="stat-card-value" style={{ color: "#0f9b8e" }}>{stats.instructorCount}</div>
        <div className="stat-card-label">Instructors evaluated this month</div>
      </div>
      {flaggedCardProps ? (
        <button
          type={flaggedCardProps.type}
          className="stat-card"
          onClick={flaggedCardProps.onClick}
          style={{
            textAlign: "left",
            border: flaggedActive ? "2px solid #c2550a" : "none",
            cursor: "pointer",
            background: flaggedActive ? "#fff7ed" : undefined,
          }}
        >
          <div className="stat-card-value" style={{ color: "#c2550a" }}>{stats.flaggedCount}</div>
          <div className="stat-card-label">
            {flaggedLabel}
            {flaggedActive ? " (Filtered)" : ""}
          </div>
        </button>
      ) : (
        <div className="stat-card">
          <div className="stat-card-value" style={{ color: "#c2550a" }}>{stats.flaggedCount}</div>
          <div className="stat-card-label">{flaggedLabel}</div>
        </div>
      )}
    </div>
  );
}
