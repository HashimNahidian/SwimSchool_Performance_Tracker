import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth";
import { getInstructorEvaluationDetail, listInstructorEvaluations } from "../api";
import type { EvaluationDetail, EvaluationSummary } from "../types";
import { EvaluationTable } from "../components/EvaluationTable";
import { EvaluationReportModal } from "../components/EvaluationReport";
import { DEMO_EVALUATIONS } from "../mockData";

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

  // The /instructor/evaluations endpoint is user-scoped; this local filter is defense-in-depth.
  const evaluations = useMemo(() => {
    if (!user?.id || isDemo) return rawEvaluations;
    return rawEvaluations.filter((e) => e.instructor_id === user.id);
  }, [rawEvaluations, user, isDemo]);

  const evaluationsByDate = useMemo(() => {
    return [...evaluations].sort((a, b) => {
      const dateA = a.session_date ? new Date(a.session_date + "T00:00:00").getTime() : 0;
      const dateB = b.session_date ? new Date(b.session_date + "T00:00:00").getTime() : 0;
      if (dateA !== dateB) return dateB - dateA;
      return b.id - a.id;
    });
  }, [evaluations]);

  async function handleViewReport(id: number) {
    if (isDemo) {
      const found = DEMO_EVALUATIONS.find((e) => e.id === id);
      if (found) setReportEval({ ...found, notes: "Demo evaluation - no real data.", ratings: [] });
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
          <span>Demo mode</span>
          <span>Showing sample data. Connect to the API to see your real evaluations.</span>
        </div>
      )}

      <div className="page-heading">
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
          <h1 className="page-title">Welcome back, {user?.name ?? "Instructor"}</h1>
          <span className="privacy-badge">Your evaluations only</span>
        </div>
      </div>

      <div className="card">
        <h2>
          My Evaluations{" "}
          {loadingReport && <span style={{ fontSize: 13, color: "#64748b", fontWeight: 400 }}>Loading...</span>}
        </h2>
        {evaluationsByDate.length > 0 ? (
          <EvaluationTable rows={evaluationsByDate} onView={handleViewReport} />
        ) : (
          <p style={{ color: "#64748b", fontSize: 14 }}>No evaluations yet.</p>
        )}
      </div>

      {reportEval && <EvaluationReportModal evaluation={reportEval} onClose={() => setReportEval(null)} />}
    </>
  );
}
