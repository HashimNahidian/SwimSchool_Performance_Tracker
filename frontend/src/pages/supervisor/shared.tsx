import { FormEvent, useEffect, useMemo, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { useAuth } from "../../auth";
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
} from "../../api";
import type {
  Attribute,
  EvaluationDetail,
  EvaluationSummary,
  Level,
  ReevaluationRequest,
  Skill,
  User,
} from "../../types";
import { currentMonthStats } from "../../components/EvaluationMonthlyStats";

export type ReevaluationPrefill = {
  evaluationId: number;
  instructorId: number;
  skillId: number;
};

type SupervisorFilters = {
  instructorId: string;
  supervisorId: string;
  skillId: string;
  finalGrade: string;
  needsReevaluation: string;
  dateFrom: string;
  dateTo: string;
  sortOption: string;
  selectedDays: number[];
};

const DEFAULT_FILTERS: SupervisorFilters = {
  instructorId: "",
  supervisorId: "",
  skillId: "",
  finalGrade: "",
  needsReevaluation: "",
  dateFrom: "",
  dateTo: "",
  sortOption: "created_at:desc",
  selectedDays: [],
};

const RATING_LABEL: Record<number, string> = {
  1: "1 - Does not meet Standards",
  2: "2 - Needs Improvement",
  3: "3 - Meets Standard",
  4: "4 - Exceeds Standard",
  5: "5 - Outstanding",
};

export function useSupervisorData() {
  const { token, user } = useAuth();
  const [error, setError] = useState("");
  const [users, setUsers] = useState<User[]>([]);
  const [levels, setLevels] = useState<Level[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationSummary[]>([]);
  const [reevaluations, setReevaluations] = useState<ReevaluationRequest[]>([]);
  const [needsReevalMode, setNeedsReevalMode] = useState(false);
  const [reportEval, setReportEval] = useState<EvaluationDetail | null>(null);
  const [editEval, setEditEval] = useState<EvaluationDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [filters, setFilters] = useState<SupervisorFilters>(DEFAULT_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<SupervisorFilters>(DEFAULT_FILTERS);

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

  function applyFilters() {
    setAppliedFilters(filters);
  }

  function clearFilters() {
    setFilters(DEFAULT_FILTERS);
    setAppliedFilters(DEFAULT_FILTERS);
    setNeedsReevalMode(false);
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
    setEvaluations((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
    refreshData();
    setEditEval(null);
  }

  function handleCreated(created: EvaluationDetail) {
    setEvaluations((prev) => [created, ...prev.filter((item) => item.id !== created.id)]);
    refreshData();
    setNeedsReevalMode(false);
    setFilters((prev) => ({ ...prev, needsReevaluation: "" }));
    setAppliedFilters((prev) => ({ ...prev, needsReevaluation: "" }));
  }

  const stats = useMemo(() => currentMonthStats(evaluations), [evaluations]);

  const filteredRows = useMemo(() => {
    return [...evaluations]
      .filter((row) => {
        if (appliedFilters.instructorId && row.instructor_id !== Number(appliedFilters.instructorId)) return false;
        if (appliedFilters.supervisorId && row.supervisor_id !== Number(appliedFilters.supervisorId)) return false;
        if (appliedFilters.skillId && row.skill_id !== Number(appliedFilters.skillId)) return false;
        if (appliedFilters.finalGrade && row.final_grade !== Number(appliedFilters.finalGrade)) return false;
        if (appliedFilters.needsReevaluation === "true" && !row.needs_reevaluation) return false;
        if (appliedFilters.needsReevaluation === "false" && row.needs_reevaluation) return false;
        if (appliedFilters.dateFrom && new Date(row.created_at) < new Date(appliedFilters.dateFrom)) return false;
        if (appliedFilters.dateTo) {
          const endDate = new Date(appliedFilters.dateTo);
          endDate.setHours(23, 59, 59, 999);
          if (new Date(row.created_at) > endDate) return false;
        }
        if (appliedFilters.selectedDays.length > 0 && !appliedFilters.selectedDays.includes(new Date(row.created_at).getDay())) {
          return false;
        }
        if (needsReevalMode && !row.needs_reevaluation) return false;
        return true;
      })
      .sort((a, b) => {
        const getSortValue = (row: EvaluationSummary) => {
          const [sortBy] = appliedFilters.sortOption.split(":");
          switch (sortBy) {
            case "updated_at":
              return new Date(row.updated_at).getTime();
            case "final_grade":
              return row.final_grade ?? -1;
            case "id":
              return row.id;
            case "instructor_id":
              return row.instructor_id;
            case "supervisor_id":
              return row.supervisor_id;
            default:
              return new Date(row.created_at).getTime();
          }
        };

        const valueA = getSortValue(a);
        const valueB = getSortValue(b);
        if (valueA !== valueB) {
          const [, sortDir = "desc"] = appliedFilters.sortOption.split(":");
          return sortDir === "asc" ? Number(valueA) - Number(valueB) : Number(valueB) - Number(valueA);
        }
        return b.id - a.id;
      });
  }, [appliedFilters, evaluations, needsReevalMode]);

  const filteredReevaluations = useMemo(() => {
    return reevaluations.filter((row) => {
      if (appliedFilters.instructorId && row.instructor_id !== Number(appliedFilters.instructorId)) return false;
      if (appliedFilters.skillId && row.skill_id !== Number(appliedFilters.skillId)) return false;
      return true;
    });
  }, [appliedFilters, reevaluations]);

  return {
    token,
    user,
    error,
    setError,
    users,
    levels,
    skills,
    evaluations,
    reportEval,
    setReportEval,
    editEval,
    setEditEval,
    loadingDetail,
    needsReevalMode,
    setNeedsReevalMode,
    filters,
    setFilters,
    applyFilters,
    clearFilters,
    filteredRows,
    filteredReevaluations,
    stats,
    refreshData,
    openDetail,
    handleCompleteReevaluation,
    handleSaved,
    handleCreated,
  };
}

export function SupervisorReevaluationPanel({
  users,
  skills,
  filteredReevaluations,
  filters,
  setFilters,
  onComplete,
  showControls = true,
}: {
  users: User[];
  skills: Skill[];
  filteredReevaluations: ReevaluationRequest[];
  filters: SupervisorFilters;
  setFilters: Dispatch<SetStateAction<SupervisorFilters>>;
  onComplete: (id: number) => void;
  showControls?: boolean;
}) {
  return (
    <div className="card" style={{ marginBottom: 20 }}>
      <h2 style={{ marginBottom: 12 }}>Needs Reevaluation</h2>
      {showControls && (
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
        </div>
      )}

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
                  <button type="button" onClick={() => onComplete(request.id)}>
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
  );
}

export function SupervisorCreateEvaluation({
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
  onCreated: (created: EvaluationDetail) => void;
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
  const levelSkills = useMemo(() => skills.filter((item) => item.level_id === levelId), [skills, levelId]);
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
        for (const attr of attrs) defaults[attr.id] = 3;
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
      const created = await createSupervisorEvaluation(token, {
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
      onCreated(created);
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
                  {[1, 2, 3, 4, 5].map((value) => (
                    <option key={value} value={value}>{RATING_LABEL[value]}</option>
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
