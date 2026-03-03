import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth";
import { listInstructorEvaluations } from "../api";
import type { EvaluationSummary } from "../types";
import { EvaluationTable } from "../components/EvaluationTable";
import { DonutChart } from "../components/DonutChart";

export function InstructorPage() {
  const { token, user } = useAuth();
  const [evaluations, setEvaluations] = useState<EvaluationSummary[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    listInstructorEvaluations(token)
      .then(setEvaluations)
      .catch((e: Error) => setError(e.message));
  }, [token]);

  const { submitted, draft, total, completionRate, skillEntries, recent } = useMemo(() => {
    let submitted = 0;
    let draft = 0;
    const skillCounts: Record<string, number> = {};
    for (const r of evaluations) {
      if (r.status === "SUBMITTED") submitted++;
      else draft++;
      skillCounts[r.skill_name] = (skillCounts[r.skill_name] ?? 0) + 1;
    }
    const total = evaluations.length;
    return {
      submitted,
      draft,
      total,
      completionRate: total > 0 ? Math.round((submitted / total) * 100) : 0,
      skillEntries: Object.entries(skillCounts).sort((a, b) => b[1] - a[1]),
      recent: evaluations.slice(0, 5),
    };
  }, [evaluations]);

  return (
    <>
      {error && <p className="error">{error}</p>}

      <div className="page-heading">
        <h1 className="page-title">Welcome back, {user?.name ?? "Instructor"}</h1>
        <p className="page-subtitle">Here's your performance overview.</p>
      </div>

      <div className="two-col">
        <div className="card">
          <h2>Performance Summary</h2>
          <div className="perf-rate">{completionRate}%</div>
          <p className="perf-rate-label">Completion Rate</p>
          <div className="perf-stats-row">
            <div className="perf-stat">
              <span className="perf-stat-val">{total}</span>
              <span className="perf-stat-lbl">Total</span>
            </div>
            <div className="perf-stat">
              <span className="perf-stat-val">{submitted}</span>
              <span className="perf-stat-lbl">Submitted</span>
            </div>
            <div className="perf-stat">
              <span className="perf-stat-val">{draft}</span>
              <span className="perf-stat-lbl">Pending</span>
            </div>
          </div>
        </div>

        <div className="card">
          <h2>Performance Distribution</h2>
          <DonutChart submitted={submitted} draft={draft} total={total} />
        </div>
      </div>

      <div className="card">
        <h2>Recent Evaluations</h2>
        {recent.length > 0 ? (
          <EvaluationTable rows={recent} />
        ) : (
          <p style={{ color: "#64748b", fontSize: 14 }}>No evaluations yet.</p>
        )}
      </div>

      {skillEntries.length > 0 && (
        <div className="card">
          <h2>Skill Focus</h2>
          {skillEntries.map(([skill, count]) => (
            <div key={skill} className="skill-bar-row">
              <span className="skill-bar-label">{skill}</span>
              <div className="skill-bar-track">
                <div
                  className="skill-bar-fill"
                  style={{ width: `${(count / total) * 100}%` }}
                />
              </div>
              <span className="skill-bar-count">{count}</span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
