import { FormEvent, useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth";
import {
  createSupervisorEvaluation,
  getSupervisorEvaluationDetail,
  listSupervisorEvaluations,
  listSupervisorInstructors,
  listSupervisorLevels,
  listSupervisorSkillAttributes,
  listSupervisorSkills,
} from "../api";
import type { Attribute, EvaluationDetail, EvaluationSummary, Level, Skill, User } from "../types";
import { EvaluationTable } from "../components/EvaluationTable";
import { EvaluationReportModal } from "../components/EvaluationReport";
import { EvaluationEditModal } from "../components/EvaluationEditModal";
export function SupervisorPage() {
  const { token, user } = useAuth();
  const [error, setError] = useState("");
  const [users, setUsers] = useState<User[]>([]);
  const [levels, setLevels] = useState<Level[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationSummary[]>([]);
  const [showCreate, setShowCreate] = useState(false);

  const [reportEval, setReportEval] = useState<EvaluationDetail | null>(null);
  const [editEval, setEditEval] = useState<EvaluationDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    if (!token) return;
    Promise.all([listSupervisorInstructors(token), listSupervisorLevels(token), listSupervisorSkills(token), listSupervisorEvaluations(token)])
      .then(([u, l, s, e]) => {
        setUsers(u);
        setLevels(l);
        setSkills(s);
        setEvaluations(e);
      })
      .catch((e: Error) => setError(e.message));
  }, [token]);

  function refreshEvaluations() {
    if (!token) return;
    listSupervisorEvaluations(token)
      .then((e) => setEvaluations(e))
      .catch((e: Error) => setError(e.message));
  }

  async function openDetail(id: number, mode: "view" | "edit") {
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
    setEvaluations((prev) => prev.map((e) => (e.id === updated.id ? { ...e } : e)));
    setEditEval(null);
  }

  const { instructorCount, total } = useMemo(() => {
    const instructors = new Set<string>();
    for (const r of evaluations) {
      instructors.add(r.instructor_name);
    }
    return {
      instructorCount: instructors.size,
      total: evaluations.length,
    };
  }, [evaluations]);

  const allRows = useMemo(() => {
    return [...evaluations].sort((a, b) => {
      const dateA = new Date(a.created_at).getTime();
      const dateB = new Date(b.created_at).getTime();
      if (dateA !== dateB) return dateB - dateA;
      return b.id - a.id;
    });
  }, [evaluations]);

  if (!token) return null;

  return (
    <>
      {error && <p className="error">{error}</p>}

      <div className="page-heading">
        <h1 className="page-title">Welcome back, {user?.full_name ?? "Supervisor"}</h1>
        <p className="page-subtitle">Manage and track instructor evaluations across all swim levels.</p>
      </div>

      <div className="stat-cards supervisor-stat-cards">
        <div className="stat-card">
          <div className="stat-card-value" style={{ color: "#023e8a" }}>{total}</div>
          <div className="stat-card-label">Total Evaluations</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-value" style={{ color: "#0f9b8e" }}>{instructorCount}</div>
          <div className="stat-card-label">Instructors Evaluated</div>
        </div>
      </div>


      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ marginBottom: 0 }}>
            Evaluations
            {loadingDetail && <span style={{ fontSize: 13, color: "#64748b", fontWeight: 400, marginLeft: 8 }}>Loading...</span>}
          </h2>
          <button className="btn-add" onClick={() => setShowCreate((p) => !p)}>
            {showCreate ? "Cancel" : "+ New Evaluation"}
          </button>
        </div>

        <EvaluationTable
          rows={allRows}
          onView={(id) => openDetail(id, "view")}
          onEdit={(id) => openDetail(id, "edit")}
        />
        {allRows.length === 0 && (
          <p style={{ color: "#64748b", fontSize: 14, paddingTop: 8 }}>No evaluations yet.</p>
        )}
      </div>

      {showCreate && (
        <SupervisorCreateEvaluation
          token={token}
          users={users}
          levels={levels}
          skills={skills}
          onCreated={() => {
            refreshEvaluations();
            setShowCreate(false);
          }}
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

const RATING_LABEL: Record<number, string> = {
  1: "1 - Does not meet Standards",
  2: "2 - Needs Improvement",
  3: "3 - Meets Standard",
  4: "4 - Exceeds Standard",
  5: "5 - Outstanding",
};

function SupervisorCreateEvaluation({
  token,
  users,
  levels,
  skills,
  onCreated,
}: {
  token: string;
  users: User[];
  levels: Level[];
  skills: Skill[];
  onCreated: () => void;
}) {
  const [instructorId, setInstructorId] = useState<number>(users[0]?.id ?? 0);
  const [levelId, setLevelId] = useState<number>(levels[0]?.id ?? 0);
  const [skillId, setSkillId] = useState<number>(0);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [attributes, setAttributes] = useState<Attribute[]>([]);
  const [ratings, setRatings] = useState<Record<number, number>>({});
  const levelSkills = useMemo(() => skills.filter((x) => x.level_id === levelId), [skills, levelId]);

  useEffect(() => {
    if (users.length > 0 && !instructorId) setInstructorId(users[0].id);
  }, [instructorId, users]);

  useEffect(() => {
    if (levels.length > 0 && !levelId) setLevelId(levels[0].id);
  }, [levelId, levels]);

  useEffect(() => {
    if (levelSkills.length > 0) setSkillId(levelSkills[0].id);
  }, [levelSkills]);

  useEffect(() => {
    if (!skillId) return;
    listSupervisorSkillAttributes(token, skillId)
      .then((attrs) => {
        setAttributes(attrs);
        const defaults: Record<number, number> = {};
        for (const a of attrs) defaults[a.id] = 3;
        setRatings(defaults);
      })
      .catch(() => {
        setAttributes([]);
        setRatings({});
      });
  }, [skillId, token]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await createSupervisorEvaluation(token, {
        instructor_id: instructorId,
        skill_id: skillId,
        notes: notes.trim() || undefined,
        ratings: Object.entries(ratings).map(([id, value]) => ({
          attribute_id: Number(id),
          rating: value,
        })),
      });
      setNotes("");
      onCreated();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="card">
      <h2>Create Evaluation</h2>
      <form className="form" onSubmit={onSubmit}>
        <label>
          Instructor
          <select value={instructorId} onChange={(e) => setInstructorId(Number(e.target.value))}>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.full_name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Swim Level
          <select value={levelId} onChange={(e) => setLevelId(Number(e.target.value))}>
            {levels.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Stroke / Skill
          <select value={skillId} onChange={(e) => setSkillId(Number(e.target.value))}>
            {levelSkills.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>

        {attributes.length > 0 && (
          <fieldset className="edit-ratings-fieldset">
            <legend style={{ fontWeight: 700, color: "#023e8a", padding: "0 6px" }}>
              Performance Ratings
            </legend>
            {attributes.map((attr) => (
              <label key={attr.id} className="inline-rating edit-rating-row">
                <span className="edit-rating-label">{attr.name}</span>
                <select
                  value={ratings[attr.id] ?? 3}
                  onChange={(e) =>
                    setRatings((prev) => ({ ...prev, [attr.id]: Number(e.target.value) }))
                  }
                >
                  {[1, 2, 3, 4, 5].map((v) => (
                    <option key={v} value={v}>{RATING_LABEL[v]}</option>
                  ))}
                </select>
              </label>
            ))}
          </fieldset>
        )}

        <label>
          Notes
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Optional coaching notes..."
          />
        </label>

        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={levelSkills.length === 0}>Create Evaluation</button>
      </form>
    </div>
  );
}
