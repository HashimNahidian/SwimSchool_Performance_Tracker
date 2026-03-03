import type { EvaluationSummary } from "../types";

export function EvaluationTable({ rows }: { rows: EvaluationSummary[] }) {
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
          <th>Status</th>
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
            <td>
              <span className={row.status === "SUBMITTED" ? "badge-submitted" : "badge-draft"}>
                {row.status}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
