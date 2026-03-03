import { FormEvent, useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth";
import {
  createSupervisorEvaluation,
  listLevels,
  listSkills,
  listSupervisorEvaluations,
  listUsers,
  resolveSupervisorTemplate,
} from "../api";
import type { EvaluationSummary, Level, Skill, TemplateResolved, User } from "../types";
import { EvaluationTable } from "../components/EvaluationTable";

export function SupervisorPage() {
  const { token, user } = useAuth();
  const [error, setError] = useState("");
  const [users, setUsers] = useState<User[]>([]);
  const [levels, setLevels] = useState<Level[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationSummary[]>([]);
  const [evalTab, setEvalTab] = useState<"inprogress" | "scheduled">("inprogress");
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    if (!token) return;
    Promise.all([listUsers(token), listLevels(token), listSkills(token), listSupervisorEvaluations(token)])
      .then(([u, l, s, e]) => {
        setUsers(u.filter((x) => x.role === "INSTRUCTOR"));
        setLevels(l);
        setSkills(s);
        setEvaluations(e);
      })
      .catch((e: Error) => setError(e.message));
  }, [token]);

  function refreshEvaluations() {
    if (!token) return;
    listSupervisorEvaluations(token)
      .then(setEvaluations)
      .catch((e: Error) => setError(e.message));
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

  return (
    <>
      {error && <p className="error">{error}</p>}

      <div className="page-heading">
        <h1 className="page-title">Welcome back, {user?.name ?? "Supervisor"}</h1>
        <p className="page-subtitle">Manage and track instructor evaluations.</p>
      </div>

      {drafts.length > 0 && (
        <div className="key-insight">
          <span className="key-insight-icon">💡</span>
          <span className="key-insight-text">
            You have <strong>{drafts.length}</strong> draft evaluation
            {drafts.length !== 1 ? "s" : ""} pending submission.
          </span>
        </div>
      )}

      <div className="card">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 16,
          }}
        >
          <h2 style={{ marginBottom: 0 }}>Evaluations</h2>
          <button
            className="btn-add"
            onClick={() => setShowCreate((p) => !p)}
          >
            {showCreate ? "✕ Cancel" : "+ New Evaluation"}
          </button>
        </div>

        <div className="sub-tabs">
          <button
            className={`sub-tab${evalTab === "inprogress" ? " active" : ""}`}
            onClick={() => setEvalTab("inprogress")}
          >
            In Progress ({drafts.length})
          </button>
          <button
            className={`sub-tab${evalTab === "scheduled" ? " active" : ""}`}
            onClick={() => setEvalTab("scheduled")}
          >
            Completed ({submitted.length})
          </button>
        </div>

        <EvaluationTable rows={tabRows} />
        {tabRows.length === 0 && (
          <p style={{ color: "#64748b", fontSize: 14, paddingTop: 8 }}>
            No evaluations in this category.
          </p>
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
    </>
  );
}

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
  const [sessionLabel, setSessionLabel] = useState("");
  const [sessionDate, setSessionDate] = useState("");
  const [notes, setNotes] = useState("");
  const [criteria, setCriteria] = useState<TemplateResolved["attributes"]>([]);
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
    if (!levelId || !skillId) {
      setCriteria([]);
      setRatings({});
      return;
    }
    resolveSupervisorTemplate(token, levelId, skillId)
      .then((tmpl) => {
        setCriteria(tmpl.attributes);
        const r: Record<number, number> = {};
        for (const item of tmpl.attributes) r[item.attribute_id] = 2;
        setRatings(r);
      })
      .catch(() => {
        setCriteria([]);
        setRatings({});
      });
  }, [token, levelId, skillId]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    await createSupervisorEvaluation(token, {
      instructor_id: instructorId,
      level_id: levelId,
      skill_id: skillId,
      session_label: sessionLabel,
      session_date: sessionDate,
      notes,
      ratings: criteria.map((c) => ({
        attribute_id: c.attribute_id,
        rating_value: ratings[c.attribute_id] ?? 2,
      })),
    });
    setSessionLabel("");
    setSessionDate("");
    setNotes("");
    onCreated();
  }

  return (
    <div className="card">
      <h2>Create Evaluation</h2>
      <form className="form" onSubmit={onSubmit}>
        <label>
          Instructor
          <select
            value={instructorId}
            onChange={(e) => setInstructorId(Number(e.target.value))}
          >
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Level
          <select
            value={levelId}
            onChange={(e) => setLevelId(Number(e.target.value))}
          >
            {levels.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Skill
          <select
            value={skillId}
            onChange={(e) => setSkillId(Number(e.target.value))}
          >
            {levelSkills.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Session Label
          <input
            value={sessionLabel}
            onChange={(e) => setSessionLabel(e.target.value)}
            required
          />
        </label>
        <label>
          Session Date
          <input
            type="date"
            value={sessionDate}
            onChange={(e) => setSessionDate(e.target.value)}
            required
          />
        </label>
        <label>
          Notes
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
        <fieldset style={{ padding: 12, borderRadius: 8, border: "1px solid #bfd2e0" }}>
          <legend style={{ fontWeight: 700, color: "#0a3d62", padding: "0 6px" }}>
            Ratings
          </legend>
          <p style={{ fontSize: 13, color: "#64748b", marginBottom: 10 }}>
            Default is 2 (Meets) for each criterion.
          </p>
          {criteria.map((c) => (
            <label key={c.attribute_id} className="inline-rating">
              <span>{c.attribute_name}</span>
              <select
                value={ratings[c.attribute_id] ?? 2}
                onChange={(e) =>
                  setRatings((p) => ({ ...p, [c.attribute_id]: Number(e.target.value) }))
                }
              >
                <option value={1}>1 Remediate</option>
                <option value={2}>2 Meets</option>
                <option value={3}>3 Exceeds</option>
              </select>
            </label>
          ))}
          {criteria.length === 0 && (
            <p className="error">No template criteria found for selected level/skill.</p>
          )}
        </fieldset>
        <button type="submit" disabled={criteria.length === 0}>
          Save Draft
        </button>
      </form>
    </div>
  );
}
