import type { EvaluationSummary } from "../types";

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "2-digit" });
}

const ACTION_BUTTON_STYLE = {
  padding: "4px 10px",
  fontSize: 12,
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  gap: 6,
  whiteSpace: "nowrap" as const,
};

const GRADE_LABEL: Record<number, string> = {
  1: "Does not meet Standards",
  2: "Needs Improvement",
  3: "Meets Standard",
  4: "Exceeds Standard",
  5: "Outstanding",
};

export function EvaluationTable({
  rows,
  onView,
  onEdit,
  onDelete,
  onReevaluate,
}: {
  rows: EvaluationSummary[];
  onView?: (id: number) => void;
  onEdit?: (id: number) => void;
  onDelete?: (id: number) => void;
  onReevaluate?: (id: number) => void;
}) {
  const hasActions = onView !== undefined || onEdit !== undefined || onDelete !== undefined || onReevaluate !== undefined;

  return (
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Instructor</th>
          <th>Supervisor</th>
          <th>Level</th>
          <th>Skill</th>
          <th>Grade</th>
          <th>Date</th>
          {hasActions && <th>Actions</th>}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr
            key={row.id}
            style={row.needs_reevaluation || (row.final_grade ?? 99) <= 2 ? { background: "#fff4e5" } : undefined}
          >
            <td>{row.id}</td>
            <td>{row.instructor_name}</td>
            <td>{row.supervisor_name}</td>
            <td>{row.level_name}</td>
            <td>{row.skill_name}</td>
            <td>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <span>{row.final_grade != null ? `${row.final_grade} — ${GRADE_LABEL[row.final_grade] ?? ""}` : "—"}</span>
                {row.needs_reevaluation && (
                  <span
                    style={{
                      background: "#c2550a",
                      color: "white",
                      borderRadius: 999,
                      padding: "2px 8px",
                      fontSize: 11,
                      fontWeight: 700,
                    }}
                  >
                    Needs Reevaluation
                  </span>
                )}
              </div>
            </td>
            <td>{fmtDate(row.created_at)}</td>
            {hasActions && (
              <td>
                <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "nowrap" }}>
                  {onView && (
                    <button style={ACTION_BUTTON_STYLE} onClick={() => onView(row.id)}>
                      📄 View
                    </button>
                  )}
                  {onEdit && (
                    <button
                      style={{ ...ACTION_BUTTON_STYLE, background: "#0096c7" }}
                      onClick={() => onEdit(row.id)}
                    >
                      ✏ Edit
                    </button>
                  )}
                  {onReevaluate && row.needs_reevaluation && (
                    <button
                      style={{ ...ACTION_BUTTON_STYLE, background: "#0f9b8e" }}
                      onClick={() => onReevaluate(row.id)}
                    >
                      Reevaluate
                    </button>
                  )}
                  {onDelete && (
                    <button
                      style={{ ...ACTION_BUTTON_STYLE, background: "#4fb3d9" }}
                      onClick={() => onDelete(row.id)}
                    >
                      🗑 Delete
                    </button>
                  )}
                </div>
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
