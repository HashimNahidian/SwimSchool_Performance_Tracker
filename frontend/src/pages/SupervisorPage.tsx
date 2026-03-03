import { FormEvent, useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth";
import {
  createSupervisorEvaluation,
  getSupervisorEvaluationDetail,
  listLevels,
  listSkills,
  listSupervisorEvaluations,
  listUsers,
  resolveSupervisorTemplate,
} from "../api";
import type { EvaluationDetail, EvaluationSummary, Level, Skill, TemplateResolved, User } from "../types";
import { EvaluationTable } from "../components/EvaluationTable";
import { DonutChart } from "../components/DonutChart";
import { BarChart } from "../components/BarChart";
import { EvaluationReportModal } from "../components/EvaluationReport";
import { EvaluationEditModal } from "../components/EvaluationEditModal";
import { DEMO_EVALUATIONS } from "../mockData";

function monthLabel(dateStr: string) {
  return new Date(dateStr + "T00:00:00").toLocaleDateString("en-US", { month: "short", year: "2-digit" });
}

export function SupervisorPage() {
  const { token, user } = useAuth();
  const [error, setError] = useState("");
  const [users, setUsers] = useState<User[]>([]);
  const [levels, setLevels] = useState<Level[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationSummary[]>([]);
  const [evalTab, setEvalTab] = useState<"inprogress" | "scheduled">("inprogress");
  const [showCreate, setShowCreate] = useState(false);
  const [isDemo, setIsDemo] = useState(false);

  const [reportEval, setReportEval] = useState<EvaluationDetail | null>(null);
  const [editEval, setEditEval] = useState<EvaluationDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    if (!token) return;
    Promise.all([listUsers(token), listLevels(token), listSkills(token), listSupervisorEvaluations(token)])
      .then(([u, l, s, e]) => {
        setUsers(u.filter((x) => x.role === "INSTRUCTOR"));
        setLevels(l);
        setSkills(s);
        if (e.length === 0) {
          setEvaluations(DEMO_EVALUATIONS.filter((ev) => ev.supervisor_id === 201));
          setIsDemo(true);
        } else {
          setEvaluations(e);
        }
      })
      .catch((e: Error) => {
        setError(e.message);
        setEvaluations(DEMO_EVALUATIONS.filter((ev) => ev.supervisor_id === 201));
        setIsDemo(true);
      });
  }, [token]);

  function refreshEvaluations() {
    if (!token) return;
    listSupervisorEvaluations(token)
      .then((e) => {
        if (e.length === 0) {
          setEvaluations(DEMO_EVALUATIONS.filter((ev) => ev.supervisor_id === 201));
          setIsDemo(true);
        } else {
          setEvaluations(e);
          setIsDemo(false);
        }
      })
      .catch((e: Error) => setError(e.message));
  }

  async function openDetail(id: number, mode: "view" | "edit") {
    if (isDemo) {
      const found = DEMO_EVALUATIONS.find((e) => e.id === id);
      if (found) {
        const detail: EvaluationDetail = { ...found, notes: "Demo evaluation — no live data.", ratings: [] };
        mode === "view" ? setReportEval(detail) : setEditEval(detail);
      }
      return;
    }
    if (!token) return;
    setLoadingDetail(true);
    try {
      const detail = await getSupervisorEvaluationDetail(token, id);
      mode === "view" ? setReportEval(detail) : setEditEval(detail);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoadingDetail(false);
    }
  }

  function handleSaved(updated: EvaluationDetail) {
    setEvaluations((prev) => prev.map((e) => (e.id === updated.id ? { ...e } : e)));
    setEditEval(null);
  }

  function handleSubmitted(updated: EvaluationDetail) {
    setEvaluations((prev) =>
      prev.map((e) =>
        e.id === updated.id ? { ...e, status: "SUBMITTED", submitted_at: updated.submitted_at } : e
      )
    );
    setEditEval(null);
    setEvalTab("scheduled");
  }

  if (!token) return null;

  const { drafts, submitted } = useMemo(() => {
    const drafts: typeof evaluations = [];
    const submitted: typeof evaluations = [];
    for (const r of evaluations) {
      (r.status === "DRAFT" ? drafts : submitted).push(r);
    }
    return { drafts, submitted };
  }, [evaluations]);

  const tabRows = evalTab === "inprogress" ? drafts : submitted;

  const instructorData = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const r of evaluations) counts[r.instructor_name] = (counts[r.instructor_name] ?? 0) + 1;
    return Object.entries(counts).sort(([, a], [, b]) => b - a)
      .map(([label, value]) => ({ label, value, color: "#0077b6" }));
  }, [evaluations]);

  const monthlyData = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const r of evaluations) {
      if (r.session_date) {
        const key = r.session_date.slice(0, 7);
        counts[key] = (counts[key] ?? 0) + 1;
      }
    }
    return Object.entries(counts).sort(([a], [b]) => a.localeCompare(b)).slice(-6)
      .map(([month, value]) => ({ label: monthLabel(month + "-01"), value, color: "#0096c7" }));
  }, [evaluations]);

  const total = evaluations.length;

  return (
    <>
      {error && <p className="error">{error}</p>}

      {isDemo && (
        <div className="demo-banner">
          <span>🏊</span>
          <span>Demo mode — showing sample data. Connect to the API to see live evaluations.</span>
        </div>
      )}

      <div className="page-heading">
        <h1 className="page-title">Welcome back, {user?.name ?? "Supervisor"}</h1>
        <p className="page-subtitle">Manage and track instructor evaluations across all swim levels.</p>
      </div>

      <div className="stat-cards">
        <div className="stat-card">
          <div className="stat-card-value" style={{ color: "#023e8a" }}>{total}</div>
          <div className="stat-card-label">Total Evaluations</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-value" style={{ color: "#0077b6" }}>{submitted.length}</div>
          <div className="stat-card-label">Submitted</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-value" style={{ color: "#f59e0b" }}>{drafts.length}</div>
          <div className="stat-card-label">Pending</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-value" style={{ color: "#0f9b8e" }}>{instructorData.length}</div>
          <div className="stat-card-label">Instructors Evaluated</div>
        </div>
      </div>

      {drafts.length > 0 && (
        <div className="key-insight">
          <span className="key-insight-icon">🏊</span>
          <span className="key-insight-text">
            You have <strong>{drafts.length}</strong> draft evaluation{drafts.length !== 1 ? "s" : ""} pending submission.
            Click <strong>✏ Edit</strong> on any draft to review ratings and submit.
          </span>
        </div>
      )}

      <div className="two-col">
        <div className="card">
          <h2>Status Distribution</h2>
          <DonutChart submitted={submitted.length} draft={drafts.length} total={total} />
        </div>
        <div className="card">
          <h2>Monthly Sessions</h2>
          {monthlyData.length > 0 ? (
            <BarChart data={monthlyData} labelWidth={80} />
          ) : (
            <p style={{ color: "#64748b", fontSize: 14 }}>No session data yet.</p>
          )}
        </div>
      </div>

      {instructorData.length > 0 && (
        <div className="card">
          <h2>Instructor Evaluation Count</h2>
          <p className="chart-section-title">Sessions completed per instructor</p>
          <BarChart data={instructorData} />
        </div>
      )}

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ marginBottom: 0 }}>
            Evaluations
            {loadingDetail && <span style={{ fontSize: 13, color: "#64748b", fontWeight: 400, marginLeft: 8 }}>Loading...</span>}
          </h2>
          <button className="btn-add" onClick={() => setShowCreate((p) => !p)}>
            {showCreate ? "✕ Cancel" : "+ New Evaluation"}
          </button>
        </div>

        <div className="sub-tabs">
          <button className={`sub-tab${evalTab === "inprogress" ? " active" : ""}`} onClick={() => setEvalTab("inprogress")}>
            In Progress ({drafts.length})
          </button>
          <button className={`sub-tab${evalTab === "scheduled" ? " active" : ""}`} onClick={() => setEvalTab("scheduled")}>
            Completed ({submitted.length})
          </button>
        </div>

        <EvaluationTable
          rows={tabRows}
          onView={(id) => openDetail(id, "view")}
          onEdit={(id) => openDetail(id, "edit")}
        />
        {tabRows.length === 0 && (
          <p style={{ color: "#64748b", fontSize: 14, paddingTop: 8 }}>No evaluations in this category.</p>
        )}
      </div>

      {showCreate && (
        <SupervisorCreateEvaluation
          token={token} users={users} levels={levels} skills={skills}
          onCreated={() => { refreshEvaluations(); setShowCreate(false); }}
        />
      )}

      {reportEval && <EvaluationReportModal evaluation={reportEval} onClose={() => setReportEval(null)} />}

      {editEval && (
        <EvaluationEditModal
          token={token}
          evaluation={editEval}
          onSaved={handleSaved}
          onSubmitted={handleSubmitted}
          onClose={() => setEditEval(null)}
        />
      )}
    </>
  );
}

function SupervisorCreateEvaluation({
  token, users, levels, skills, onCreated,
}: { token: string; users: User[]; levels: Level[]; skills: Skill[]; onCreated: () => void }) {
  const [instructorId, setInstructorId] = useState<number>(users[0]?.id ?? 0);
  const [levelId, setLevelId] = useState<number>(levels[0]?.id ?? 0);
  const [skillId, setSkillId] = useState<number>(0);
  const [sessionLabel, setSessionLabel] = useState("");
  const [sessionDate, setSessionDate] = useState("");
  const [notes, setNotes] = useState("");
  const [criteria, setCriteria] = useState<TemplateResolved["attributes"]>([]);
  const [ratings, setRatings] = useState<Record<number, number>>({});
  const levelSkills = useMemo(() => skills.filter((x) => x.level_id === levelId), [skills, levelId]);

  useEffect(() => { if (users.length > 0 && !instructorId) setInstructorId(users[0].id); }, [instructorId, users]);
  useEffect(() => { if (levels.length > 0 && !levelId) setLevelId(levels[0].id); }, [levelId, levels]);
  useEffect(() => { if (levelSkills.length > 0) setSkillId(levelSkills[0].id); }, [levelSkills]);

  useEffect(() => {
    if (!levelId || !skillId) { setCriteria([]); setRatings({}); return; }
    resolveSupervisorTemplate(token, levelId, skillId)
      .then((tmpl) => {
        setCriteria(tmpl.attributes);
        const r: Record<number, number> = {};
        for (const item of tmpl.attributes) r[item.attribute_id] = 2;
        setRatings(r);
      })
      .catch(() => { setCriteria([]); setRatings({}); });
  }, [token, levelId, skillId]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await createSupervisorEvaluation(token, {
      instructor_id: instructorId, level_id: levelId, skill_id: skillId,
      session_label: sessionLabel, session_date: sessionDate, notes,
      ratings: criteria.map((c) => ({ attribute_id: c.attribute_id, rating_value: ratings[c.attribute_id] ?? 2 })),
    });
    setSessionLabel(""); setSessionDate(""); setNotes(""); onCreated();
  }

  return (
    <div className="card">
      <h2>Create Evaluation</h2>
      <form className="form" onSubmit={onSubmit}>
        <label>Instructor
          <select value={instructorId} onChange={(e) => setInstructorId(Number(e.target.value))}>
            {users.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
          </select>
        </label>
        <label>Swim Level
          <select value={levelId} onChange={(e) => setLevelId(Number(e.target.value))}>
            {levels.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
          </select>
        </label>
        <label>Stroke / Skill
          <select value={skillId} onChange={(e) => setSkillId(Number(e.target.value))}>
            {levelSkills.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </label>
        <label>Session Label
          <input value={sessionLabel} onChange={(e) => setSessionLabel(e.target.value)} placeholder="e.g. Morning Lanes A" required />
        </label>
        <label>Session Date
          <input type="date" value={sessionDate} onChange={(e) => setSessionDate(e.target.value)} required />
        </label>
        <label>Notes
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional coaching notes..." />
        </label>
        <fieldset style={{ padding: 12, borderRadius: 8, border: "1px solid #bbd6ea" }}>
          <legend style={{ fontWeight: 700, color: "#023e8a", padding: "0 6px" }}>Performance Ratings</legend>
          <p style={{ fontSize: 13, color: "#64748b", marginBottom: 10 }}>
            1 = Remediate &nbsp;·&nbsp; 2 = Meets Standard &nbsp;·&nbsp; 3 = Exceeds Standard
          </p>
          {criteria.map((c) => (
            <label key={c.attribute_id} className="inline-rating">
              <span>{c.attribute_name}</span>
              <select value={ratings[c.attribute_id] ?? 2}
                onChange={(e) => setRatings((p) => ({ ...p, [c.attribute_id]: Number(e.target.value) }))}>
                <option value={1}>1 — Remediate</option>
                <option value={2}>2 — Meets Standard</option>
                <option value={3}>3 — Exceeds Standard</option>
              </select>
            </label>
          ))}
          {criteria.length === 0 && <p className="error">No template criteria found for selected level / skill.</p>}
        </fieldset>
        <button type="submit" disabled={criteria.length === 0}>Save Draft</button>
      </form>
    </div>
  );
}
