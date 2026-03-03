import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth";
import { listInstructorEvaluations } from "../api";
import type { EvaluationSummary } from "../types";
import { EvaluationTable } from "../components/EvaluationTable";
import { DonutChart } from "../components/DonutChart";
import { BarChart } from "../components/BarChart";
import { DEMO_EVALUATIONS } from "../mockData";

function monthLabel(dateStr: string) {
  return new Date(dateStr + "T00:00:00").toLocaleDateString("en-US", { month: "short", year: "2-digit" });
}

export function InstructorPage() {
  const { token, user } = useAuth();
  const [rawEvaluations, setRawEvaluations] = useState<EvaluationSummary[]>([]);
  const [error, setError] = useState("");
  const [isDemo, setIsDemo] = useState(false);

  useEffect(() => {
    if (!token) return;
    listInstructorEvaluations(token)
      .then((data) => {
        if (data.length === 0) {
          // Use demo data for the logged-in user's role view
          setRawEvaluations(DEMO_EVALUATIONS.filter((e) => e.instructor_id === 101));
          setIsDemo(true);
        } else {
          setRawEvaluations(data);
          setIsDemo(false);
        }
      })
      .catch((e: Error) => {
        setError(e.message);
        setRawEvaluations(DEMO_EVALUATIONS.filter((e) => e.instructor_id === 101));
        setIsDemo(true);
      });
  }, [token]);

  // PRIVACY: Strictly filter to only this instructor's evaluations (defense-in-depth).
  // The server-side /instructor/evaluations endpoint already enforces this via JWT.
  // This client-side filter adds a second layer of protection.
  const evaluations = useMemo(() => {
    if (!user?.id || isDemo) return rawEvaluations;
    return rawEvaluations.filter((e) => e.instructor_id === user.id);
  }, [rawEvaluations, user, isDemo]);

  const { submitted, draft, total, completionRate, skillEntries, recentMonths, recent } = useMemo(() => {
    let submitted = 0;
    let draft = 0;
    const skillCounts: Record<string, number> = {};
    const monthCounts: Record<string, number> = {};

    for (const r of evaluations) {
      if (r.status === "SUBMITTED") submitted++;
      else draft++;
      skillCounts[r.skill_name] = (skillCounts[r.skill_name] ?? 0) + 1;
      if (r.session_date) {
        const key = r.session_date.slice(0, 7);
        monthCounts[key] = (monthCounts[key] ?? 0) + 1;
      }
    }

    const total = evaluations.length;
    const recentMonths = Object.entries(monthCounts)
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-6)
      .map(([month, value]) => ({
        label: monthLabel(month + "-01"),
        value,
        color: "#0077b6",
      }));

    return {
      submitted,
      draft,
      total,
      completionRate: total > 0 ? Math.round((submitted / total) * 100) : 0,
      skillEntries: Object.entries(skillCounts).sort((a, b) => b[1] - a[1]),
      recentMonths,
      recent: evaluations.slice(0, 5),
    };
  }, [evaluations]);

  return (
    <>
      {error && <p className="error">{error}</p>}

      {isDemo && (
        <div className="demo-banner">
          <span>🏊</span>
          <span>Demo mode — showing sample data. Connect to the API to see your real evaluations.</span>
        </div>
      )}

      <div className="page-heading">
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
          <h1 className="page-title">Welcome back, {user?.name ?? "Instructor"}</h1>
          <span className="privacy-badge">🔒 Your evaluations only</span>
        </div>
        <p className="page-subtitle">Track your sessions and performance across all swim levels.</p>
      </div>

      {/* Top stat cards */}
      <div className="stat-cards">
        <div className="stat-card">
          <div className="stat-card-value" style={{ color: "#023e8a" }}>{total}</div>
          <div className="stat-card-label">Total Sessions</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-value" style={{ color: "#0077b6" }}>{submitted}</div>
          <div className="stat-card-label">Submitted</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-value" style={{ color: "#f59e0b" }}>{draft}</div>
          <div className="stat-card-label">Pending</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-value" style={{ color: "#0f9b8e" }}>{completionRate}%</div>
          <div className="stat-card-label">Completion Rate</div>
        </div>
      </div>

      <div className="two-col">
        {/* Performance distribution donut */}
        <div className="card">
          <h2>Evaluation Status</h2>
          <DonutChart submitted={submitted} draft={draft} total={total} />
        </div>

        {/* Monthly activity bar chart */}
        <div className="card">
          <h2>Monthly Activity</h2>
          {recentMonths.length > 0 ? (
            <BarChart data={recentMonths} labelWidth={80} />
          ) : (
            <p style={{ color: "#64748b", fontSize: 14 }}>No session data yet.</p>
          )}
        </div>
      </div>

      {/* Skill Focus */}
      {skillEntries.length > 0 && (
        <div className="card">
          <h2>Stroke & Skill Focus</h2>
          <p className="chart-section-title">Evaluations by skill area</p>
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

      {/* Recent evaluations table */}
      <div className="card">
        <h2>Recent Sessions</h2>
        {recent.length > 0 ? (
          <EvaluationTable rows={recent} />
        ) : (
          <p style={{ color: "#64748b", fontSize: 14 }}>No evaluations yet.</p>
        )}
      </div>
    </>
  );
}
