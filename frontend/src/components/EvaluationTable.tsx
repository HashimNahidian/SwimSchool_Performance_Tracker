import type { EvaluationSummary } from "../types";

export function EvaluationTable({
  rows,
  onView,
  onEdit,
}: {
  rows: EvaluationSummary[];
  onView?: (id: number) => void;
  onEdit?: (id: number) => void;
}) {
  const hasActions = onView !== undefined || onEdit !== undefined;

  return (
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Instructor</th>
          <th>Supervisor</th>
          <th>Level</th>
          <th>Skill</th>
          <th>Session</th>
          <th>Date</th>
          {hasActions && <th>Actions</th>}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id}>
            <td>{row.id}</td>
            <td>{row.instructor_name}</td>
            <td>{row.supervisor_name}</td>
            <td>{row.level_name}</td>
            <td>{row.skill_name}</td>
            <td>{row.session_label}</td>
            <td>{row.session_date}</td>
            {hasActions && (
              <td>
                <div style={{ display: "flex", gap: 6 }}>
                  {onView && (
                    <button style={{ padding: "4px 10px", fontSize: 12 }} onClick={() => onView(row.id)}>
                      📄 View
                    </button>
                  )}
                  {onEdit && (
                    <button
                      style={{ padding: "4px 10px", fontSize: 12, background: "#0096c7" }}
                      onClick={() => onEdit(row.id)}
                    >
                      ✏ Edit
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
