import { FormEvent, useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth";
import {
  completeSupervisorReevaluation,
  createSupervisorEvaluation,
  getSupervisorEvaluationDetail,
  listSupervisorEvaluations,
  listSupervisorInstructors,
  listSupervisorLevels,
  listSupervisorReevaluations,
  listSupervisorSkillAttributes,
  listSupervisorSkills,
} from "../api";
import type {
  Attribute,
  EvaluationDetail,
  EvaluationSummary,
  Level,
  ReevaluationRequest,
  Skill,
  User,
} from "../types";
import { EvaluationTable } from "../components/EvaluationTable";
import { EvaluationReportModal } from "../components/EvaluationReport";
import { EvaluationEditModal } from "../components/EvaluationEditModal";

type ReevaluationPrefill = {
  evaluationId: number;
  instructorId: number;
  skillId: number;
};

export function SupervisorPage() {
  const { token, user } = useAuth();
  const [error, setError] = useState("");
  const [users, setUsers] = useState<User[]>([]);
  const [levels, setLevels] = useState<Level[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationSummary[]>([]);
  const [reevaluations, setReevaluations] = useState<ReevaluationRequest[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [needsReevalMode, setNeedsReevalMode] = useState(false);
  const [reevaluationPrefill, setReevaluationPrefill] = useState<ReevaluationPrefill | null>(null);
  const [reportEval, setReportEval] = useState<EvaluationDetail | null>(null);
  const [editEval, setEditEval] = useState<EvaluationDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [filters, setFilters] = useState({
    instructorId: "",
    skillId: "",
    needsReevaluationOnly: false,
  });

  useEffect(() => {
    if (!token) return;
    Promise.all([
      listSupervisorInstructors(token),
      listSupervisorLevels(token),
      listSupervisorSkills(token),
      listSupervisorEvaluations(token),
      listSupervisorReevaluations(token),
    ])
      .then(([u, l, s, e, r]) => {
        setUsers(u);
        setLevels(l);
        setSkills(s);
        setEvaluations(e);
        setReevaluations(r);
      })
      .catch((e: Error) => setError(e.message));
  }, [token]);

  function refreshData() {
    if (!token) return;
    Promise.all([
      listSupervisorEvaluations(token),
      listSupervisorReevaluations(token),
    ])
      .then(([e, r]) => {
        setEvaluations(e);
        setReevaluations(r);
      })
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

  async function handleCompleteReevaluation(id: number) {
    if (!token) return;
    try {
      await completeSupervisorReevaluation(token, id);
      refreshData();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  function handleSaved(updated: EvaluationDetail) {
    setEvaluations((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
    refreshData();
    setEditEval(null);
  }

  const { instructorCount, total, flaggedCount } = useMemo(() => {
    const instructors = new Set<number>();
    let flagged = 0;
    for (const row of evaluations) {
      instructors.add(row.instructor_id);
      if (row.needs_reevaluation) flagged += 1;
    }
    return {
      instructorCount: instructors.size,
      total: evaluations.length,
      flaggedCount: flagged,
    };
  }, [evaluations]);

  const filteredRows = useMemo(() => {
    return [...evaluations]
      .filter((row) => {
        if (filters.instructorId && row.instructor_id !== Number(filters.instructorId)) return false;
        if (filters.skillId && row.skill_id !== Number(filters.skillId)) return false;
        if (filters.needsReevaluationOnly && !row.needs_reevaluation) return false;
        if (needsReevalMode && !row.needs_reevaluation) return false;
        return true;
      })
      .sort((a, b) => {
        const dateA = new Date(a.created_at).getTime();
        const dateB = new Date(b.created_at).getTime();
        if (dateA !== dateB) return dateB - dateA;
        return b.id - a.id;
      });
  }, [evaluations, filters]);

  const filteredReevaluations = useMemo(() => {
    return reevaluations.filter((row) => {
      if (filters.instructorId && row.instructor_id !== Number(filters.instructorId)) return false;
      if (filters.skillId && row.skill_id !== Number(filters.skillId)) return false;
      return true;
    });
  }, [reevaluations, filters]);

  function openCreateEvaluation(prefill: ReevaluationPrefill | null = null) {
    setReevaluationPrefill(prefill);
    setShowCreate(true);
  }

  function handleReevaluate(evaluationId: number) {
    const row = evaluations.find((item) => item.id === evaluationId);
    if (!row) return;
    openCreateEvaluation({
      evaluationId: row.id,
      instructorId: row.instructor_id,
      skillId: row.skill_id,
    });
  }

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
        <button
          type="button"
          className="stat-card"
          onClick={() => setNeedsReevalMode((prev) => !prev)}
          style={{
            textAlign: "left",
            border: needsReevalMode ? "2px solid #c2550a" : "none",
            cursor: "pointer",
            background: needsReevalMode ? "#fff7ed" : undefined,
          }}
        >
          <div className="stat-card-value" style={{ color: "#c2550a" }}>{flaggedCount}</div>
          <div className="stat-card-label">
            Needs Reevaluation
            {needsReevalMode ? " (Filtered)" : ""}
          </div>
        </button>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <h2 style={{ marginBottom: 12 }}>Needs Reevaluation</h2>
        <div className="form inline" style={{ marginBottom: 12 }}>
          <select
            value={filters.instructorId}
            onChange={(e) => setFilters((prev) => ({ ...prev, instructorId: e.target.value }))}
          >
            <option value="">All instructors</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.full_name}
              </option>
            ))}
          </select>
          <select
            value={filters.skillId}
            onChange={(e) => setFilters((prev) => ({ ...prev, skillId: e.target.value }))}
          >
            <option value="">All skills</option>
            {skills.map((skill) => (
              <option key={skill.id} value={skill.id}>
                {skill.name}
              </option>
            ))}
          </select>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600 }}>
            <input
              type="checkbox"
              checked={filters.needsReevaluationOnly}
              onChange={(e) => setFilters((prev) => ({ ...prev, needsReevaluationOnly: e.target.checked }))}
              style={{ width: "auto" }}
            />
            Show only flagged evaluations
          </label>
        </div>

        {filteredReevaluations.length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>Instructor</th>
                <th>Skill</th>
                <th>Requested</th>
                <th>Notes</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredReevaluations.map((request) => (
                <tr key={request.id}>
                  <td>{request.instructor_name}</td>
                  <td>{request.skill_name}</td>
                  <td>{new Date(request.requested_at).toLocaleDateString()}</td>
                  <td>{request.notes || "—"}</td>
                  <td>
                    <button type="button" onClick={() => handleCompleteReevaluation(request.id)}>
                      Mark Complete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ color: "#64748b", fontSize: 14 }}>No open reevaluation requests for the current filters.</p>
        )}
      </div>

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ marginBottom: 0 }}>
            Evaluations
            {loadingDetail && <span style={{ fontSize: 13, color: "#64748b", fontWeight: 400, marginLeft: 8 }}>Loading...</span>}
          </h2>
          <button
            className="btn-add"
            onClick={() => {
              setReevaluationPrefill(null);
              setShowCreate((p) => !p);
            }}
          >
            {showCreate ? "Cancel" : "+ New Evaluation"}
          </button>
        </div>

        {needsReevalMode && (
          <p style={{ marginTop: -4, marginBottom: 14, color: "#c2550a", fontWeight: 600 }}>
            Showing only evaluations that need reevaluation.
          </p>
        )}

        <EvaluationTable
          rows={filteredRows}
          onView={(id) => openDetail(id, "view")}
          onEdit={(id) => openDetail(id, "edit")}
          onReevaluate={handleReevaluate}
        />
        {filteredRows.length === 0 && (
          <p style={{ color: "#64748b", fontSize: 14, paddingTop: 8 }}>No evaluations match the current filters.</p>
        )}
      </div>

      {showCreate && (
        <SupervisorCreateEvaluation
          token={token}
          users={users}
          levels={levels}
          skills={skills}
          prefill={reevaluationPrefill}
          onCreated={() => {
            refreshData();
            setShowCreate(false);
            setReevaluationPrefill(null);
          }}
          onCancel={() => {
            setShowCreate(false);
            setReevaluationPrefill(null);
          }}
        />
      )}

      {reportEval && <EvaluationReportModal evaluation={reportEval} onClose={() => setReportEval(null)} />}

      {editEval && (
        <EvaluationEditModal
          token={token}
          evaluation={editEval}
          onSaved={handleSaved}
          onSubmitted={handleSaved}
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
  prefill,
  onCreated,
  onCancel,
}: {
  token: string;
  users: User[];
  levels: Level[];
  skills: Skill[];
  prefill: ReevaluationPrefill | null;
  onCreated: () => void;
  onCancel: () => void;
}) {
  const [instructorId, setInstructorId] = useState<number>(users[0]?.id ?? 0);
  const [levelId, setLevelId] = useState<number>(levels[0]?.id ?? 0);
  const [skillId, setSkillId] = useState<number>(0);
  const [notes, setNotes] = useState("");
  const [needsReevaluation, setNeedsReevaluation] = useState(false);
  const [error, setError] = useState("");
  const [attributes, setAttributes] = useState<Attribute[]>([]);
  const [ratings, setRatings] = useState<Record<number, number>>({});
  const levelSkills = useMemo(() => skills.filter((x) => x.level_id === levelId), [skills, levelId]);
  const isReevaluation = prefill !== null;

  useEffect(() => {
    if (users.length > 0 && !instructorId) setInstructorId(users[0].id);
  }, [instructorId, users]);

  useEffect(() => {
    if (levels.length > 0 && !levelId) setLevelId(levels[0].id);
  }, [levelId, levels]);

  useEffect(() => {
    if (levelSkills.length === 0) {
      setSkillId(0);
      return;
    }
    if (!levelSkills.some((skill) => skill.id === skillId)) {
      setSkillId(levelSkills[0].id);
    }
  }, [levelSkills, skillId]);

  useEffect(() => {
    if (!prefill) return;
    setInstructorId(prefill.instructorId);
    setSkillId(prefill.skillId);
    const skill = skills.find((item) => item.id === prefill.skillId);
    if (skill) {
      setLevelId(skill.level_id);
    }
  }, [prefill, skills]);

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
        needs_reevaluation: needsReevaluation,
      });
      setNotes("");
      setNeedsReevaluation(false);
      onCreated();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <h2 style={{ marginBottom: 0 }}>{isReevaluation ? "Reevaluate Instructor" : "Create Evaluation"}</h2>
        <button type="button" className="btn-add" onClick={onCancel}>Cancel</button>
      </div>
      {isReevaluation && (
        <p style={{ marginTop: 10, color: "#64748b", fontSize: 14 }}>
          Submit a follow-up evaluation for this flagged skill.
        </p>
      )}
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

        <label style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 600 }}>
          <input
            type="checkbox"
            checked={needsReevaluation}
            onChange={(e) => setNeedsReevaluation(e.target.checked)}
            style={{ width: "auto" }}
          />
          Create explicit reevaluation request
        </label>

        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={levelSkills.length === 0}>Create Evaluation</button>
      </form>
    </div>
  );
}
