import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth";
import { getInstructorEvaluationDetail, listInstructorEvaluations } from "../api";
import type { EvaluationDetail, EvaluationSummary } from "../types";
import { EvaluationTable } from "../components/EvaluationTable";
import { DonutChart } from "../components/DonutChart";
import { BarChart } from "../components/BarChart";
import { EvaluationReportModal } from "../components/EvaluationReport";
import { DEMO_EVALUATIONS } from "../mockData";

function monthLabel(dateStr: string) {
  return new Date(dateStr + "T00:00:00").toLocaleDateString("en-US", { month: "short", year: "2-digit" });
}

export function InstructorPage() {
  const { token, user } = useAuth();
  const [rawEvaluations, setRawEvaluations] = useState<EvaluationSummary[]>([]);
  const [error, setError] = useState("");
  const [isDemo, setIsDemo] = useState(false);
  const [reportEval, setReportEval] = useState<EvaluationDetail | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);

  useEffect(() => {
    if (!token) return;
    listInstructorEvaluations(token)
      .then((data) => {
        if (data.length === 0) {
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
  // The server endpoint /instructor/evaluations already enforces this via JWT.
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
      .map(([month, value]) => ({ label: monthLabel(month + "-01"), value, color: "#0077b6" }));

    return {
      submitted,
      draft,
      total,
      completionRate: total > 0 ? Math.round((submitted / total) * 100) : 0,
      skillEntries: Object.entries(skillCounts).sort((a, b) => b[1] - a[1]),
      recentMonths,
      recent: evaluations.slice(0, 10),
    };
  }, [evaluations]);

  async function handleViewReport(id: number) {
    if (isDemo) {
      // Build a fake detail from demo data
      const found = DEMO_EVALUATIONS.find((e) => e.id === id);
      if (found) setReportEval({ ...found, notes: "Demo evaluation — no real data.", ratings: [] });
      return;
    }
    if (!token) return;
    setLoadingReport(true);
    try {
      const detail = await getInstructorEvaluationDetail(token, id);
      setReportEval(detail);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoadingReport(false);
    }
  }

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
        <div className="card">
          <h2>Evaluation Status</h2>
          <DonutChart submitted={submitted} draft={draft} total={total} />
        </div>
        <div className="card">
          <h2>Monthly Activity</h2>
          {recentMonths.length > 0 ? (
            <BarChart data={recentMonths} labelWidth={80} />
          ) : (
            <p style={{ color: "#64748b", fontSize: 14 }}>No session data yet.</p>
          )}
        </div>
      </div>

      {skillEntries.length > 0 && (
        <div className="card">
          <h2>Stroke &amp; Skill Focus</h2>
          <p className="chart-section-title">Evaluations by skill area</p>
          {skillEntries.map(([skill, count]) => (
            <div key={skill} className="skill-bar-row">
              <span className="skill-bar-label">{skill}</span>
              <div className="skill-bar-track">
                <div className="skill-bar-fill" style={{ width: `${(count / total) * 100}%` }} />
              </div>
              <span className="skill-bar-count">{count}</span>
            </div>
          ))}
        </div>
      )}

      <div className="card">
        <h2>My Evaluations {loadingReport && <span style={{ fontSize: 13, color: "#64748b", fontWeight: 400 }}>Loading...</span>}</h2>
        {recent.length > 0 ? (
          <EvaluationTable rows={recent} onView={handleViewReport} />
        ) : (
          <p style={{ color: "#64748b", fontSize: 14 }}>No evaluations yet.</p>
        )}
      </div>

      {reportEval && (
        <EvaluationReportModal evaluation={reportEval} onClose={() => setReportEval(null)} />
      )}
    </>
  );
}
