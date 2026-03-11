import { FormEvent, useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth";
import type { ManagerEvaluationQuery } from "../api";
import {
  createLevel,
  createSkill,
  createUser,
  deleteLevel,
  deleteSkill,
  deleteUser,
  emailEvaluationsCsv,
  exportEvaluationsCsvUrl,
  getManagerEvaluationDetail,
  listLevels,
  listManagerEvaluationsWithQuery,
  listSkills,
  listUsers,
  updateLevel,
  updateManagerEvaluation,
  updateSkill,
  updateUser,
} from "../api";
import type { EvaluationDetail, EvaluationSummary, Level, Skill, User, UserRole } from "../types";
import { Section } from "../components/Section";
import { EvaluationTable } from "../components/EvaluationTable";
import { DonutChart } from "../components/DonutChart";
import { BarChart } from "../components/BarChart";
import { EvaluationReportModal } from "../components/EvaluationReport";
import { EvaluationEditModal } from "../components/EvaluationEditModal";
import { DEMO_EVALUATIONS, DEMO_LEVELS, DEMO_SKILLS, DEMO_USERS } from "../mockData";

type ManagerTab = "dashboard" | "users" | "levels" | "evaluations";

const MANAGER_TABS: ManagerTab[] = ["dashboard", "users", "levels", "evaluations"];

const SORT_FIELDS = new Set<NonNullable<ManagerEvaluationQuery["sort_by"]>>([
  "id", "session_date", "submitted_at", "instructor_id", "supervisor_id", "level_id", "skill_id"
]);
const EVALUATIONS_PAGE_SIZE = 25;

function parsePositiveInt(value: string): number | undefined {
  if (!value.trim()) return undefined;
  const n = Number.parseInt(value, 10);
  return Number.isNaN(n) ? undefined : n;
}

function buildQuery(filters: Record<string, string>): ManagerEvaluationQuery {
  const q: ManagerEvaluationQuery = {};
  const instructorId = parsePositiveInt(filters.instructor_id);
  const supervisorId = parsePositiveInt(filters.supervisor_id);
  const levelId = parsePositiveInt(filters.level_id);
  const skillId = parsePositiveInt(filters.skill_id);
  const ratingValue = parsePositiveInt(filters.rating_value);
  if (instructorId !== undefined) q.instructor_id = instructorId;
  if (supervisorId !== undefined) q.supervisor_id = supervisorId;
  if (levelId !== undefined) q.level_id = levelId;
  if (skillId !== undefined) q.skill_id = skillId;
  if (ratingValue !== undefined) q.rating_value = ratingValue;
  if (filters.date_from) q.date_from = filters.date_from;
  if (filters.date_to) q.date_to = filters.date_to;
  q.sort_by = SORT_FIELDS.has(filters.sort_by as NonNullable<ManagerEvaluationQuery["sort_by"]>)
    ? (filters.sort_by as NonNullable<ManagerEvaluationQuery["sort_by"]>)
    : "submitted_at";
  q.sort_dir = filters.sort_dir === "asc" ? "asc" : "desc";
  return q;
}

export function ManagerPage() {
  const { token } = useAuth();
  const [tab, setTab] = useState<ManagerTab>("dashboard");
  const [error, setError] = useState("");
  const [users, setUsers] = useState<User[]>([]);
  const [levels, setLevels] = useState<Level[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationSummary[]>([]);
  const [isDemo, setIsDemo] = useState(false);
  const [reportEval, setReportEval] = useState<EvaluationDetail | null>(null);
  const [editEval, setEditEval] = useState<EvaluationDetail | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [filters, setFilters] = useState({
    instructor_id: "", supervisor_id: "", level_id: "", skill_id: "",
    rating_value: "", date_from: "", date_to: "",
    sort_by: "submitted_at", sort_dir: "desc"
  });
  const [appliedQuery, setAppliedQuery] = useState<ManagerEvaluationQuery>({
    sort_by: "submitted_at", sort_dir: "desc", limit: EVALUATIONS_PAGE_SIZE, offset: 0
  });
  const [evaluationsPage, setEvaluationsPage] = useState(0);

  useEffect(() => {
    if (!token) return;
    Promise.all([
      listUsers(token), listLevels(token), listSkills(token),
      listManagerEvaluationsWithQuery(token, appliedQuery)
    ])
      .then(([u, l, s, e]) => {
        setUsers(u.length > 0 ? u : DEMO_USERS);
        setLevels(l.length > 0 ? l : DEMO_LEVELS);
        setSkills(s.length > 0 ? s : DEMO_SKILLS);
        if (e.length === 0) {
          setEvaluations(DEMO_EVALUATIONS);
          setIsDemo(true);
        } else {
          setEvaluations(e);
        }
      })
      .catch((e: Error) => {
        setError(e.message);
        setUsers(DEMO_USERS);
        setLevels(DEMO_LEVELS);
        setSkills(DEMO_SKILLS);
        setEvaluations(DEMO_EVALUATIONS);
        setIsDemo(true);
      });
  }, [token, appliedQuery]);

  function downloadCsv() {
    if (!token) return;
    fetch(exportEvaluationsCsvUrl(), { headers: { Authorization: `Bearer ${token}` } }).then(async (resp) => {
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "evaluations.csv"; a.click();
      URL.revokeObjectURL(url);
    });
  }

  async function sendCsvEmail(payload: {
    to: string[]; subject?: string; message?: string; filters?: ManagerEvaluationQuery;
  }) {
    if (!token) return;
    await emailEvaluationsCsv(token, payload);
  }

  async function handleViewReport(id: number) {
    if (isDemo) {
      const found = DEMO_EVALUATIONS.find((e) => e.id === id);
      if (found) setReportEval({ ...found, notes: "Demo evaluation — no live data.", ratings: [] });
      return;
    }
    if (!token) return;
    setLoadingReport(true);
    try {
      const detail = await getManagerEvaluationDetail(token, id);
      setReportEval(detail);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoadingReport(false);
    }
  }

  async function handleEditEval(id: number) {
    if (isDemo) {
      const found = DEMO_EVALUATIONS.find((e) => e.id === id);
      if (found) setEditEval({ ...found, notes: "Demo evaluation.", ratings: [
        { attribute_id: 1, attribute_name: "Water Safety", rating_value: 2 },
        { attribute_id: 2, attribute_name: "Stroke Technique", rating_value: 2 },
      ]});
      return;
    }
    if (!token) return;
    setLoadingReport(true);
    try {
      const detail = await getManagerEvaluationDetail(token, id);
      setEditEval(detail);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoadingReport(false);
    }
  }

  if (!token) return null;

  return (
    <>
      {error && <p className="error">{error}</p>}

      {isDemo && (
        <div className="demo-banner">
          <span>🏊</span>
          <span>Demo mode — showing sample data. Connect to the API to see live evaluations.</span>
        </div>
      )}

      <nav className="tabs">
        {MANAGER_TABS.map((item) => (
          <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>
            {item === "dashboard" ? "🏊 Dashboard" :
             item === "users" ? "👤 Users" :
             item === "levels" ? "🌊 Levels" :
             "📊 Evaluations"}
          </button>
        ))}
      </nav>

      {tab === "dashboard" && (
        <ManagerDashboard
          rows={evaluations}
          onGo={setTab}
          onExportCsv={downloadCsv}
          onEmailCsv={sendCsvEmail}
          appliedManagerQuery={appliedQuery}
          onView={handleViewReport}
          onEdit={handleEditEval}
        />
      )}
      {tab === "users" && (
        <ManagerUsers
          token={token}
          users={users}
          onCreated={(u) => setUsers((p) => [...p, u])}
          onUpdated={(u) => setUsers((p) => p.map((item) => (item.id === u.id ? u : item)))}
          onDeleted={(id) => setUsers((p) => p.filter((item) => item.id !== id))}
        />
      )}
      {tab === "levels" && (
        <ManagerLevels
          token={token}
          levels={levels}
          skills={skills}
          onLevelCreated={(l) => setLevels((p) => [...p, l])}
          onLevelUpdated={(l) => setLevels((p) => p.map((item) => (item.id === l.id ? l : item)))}
          onLevelDeleted={(levelId) => {
            setLevels((p) => p.filter((item) => item.id !== levelId));
            setSkills((p) => p.filter((item) => item.level_id !== levelId));
          }}
          onSkillCreated={(s) => setSkills((p) => [...p, s])}
          onSkillUpdated={(s) => setSkills((p) => p.map((item) => (item.id === s.id ? s : item)))}
          onSkillDeleted={(skillId) => setSkills((p) => p.filter((item) => item.id !== skillId))}
        />
      )}
      {tab === "evaluations" && (
        <Section title={`All Evaluations${loadingReport ? " — Loading report…" : ""}`}>
          <form className="form inline" onSubmit={(e) => { e.preventDefault(); setEvaluationsPage(0); setAppliedQuery({ ...buildQuery(filters), limit: EVALUATIONS_PAGE_SIZE, offset: 0 }); }}>
            <input placeholder="instructor id" value={filters.instructor_id}
              onChange={(e) => setFilters((p) => ({ ...p, instructor_id: e.target.value }))} />
            <input placeholder="supervisor id" value={filters.supervisor_id}
              onChange={(e) => setFilters((p) => ({ ...p, supervisor_id: e.target.value }))} />
            <select value={filters.level_id}
              onChange={(e) => setFilters((p) => ({ ...p, level_id: e.target.value }))}>
              <option value="">all levels</option>
              {levels.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
            <select value={filters.skill_id}
              onChange={(e) => setFilters((p) => ({ ...p, skill_id: e.target.value }))}>
              <option value="">all skills</option>
              {skills.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <select value={filters.rating_value}
              onChange={(e) => setFilters((p) => ({ ...p, rating_value: e.target.value }))}>
              <option value="">all ratings</option>
              <option value="1">1 — Remediate</option>
              <option value="2">2 — Meets</option>
              <option value="3">3 — Exceeds</option>
            </select>
            <select value={filters.sort_by}
              onChange={(e) => setFilters((p) => ({ ...p, sort_by: e.target.value }))}>
              <option value="submitted_at">submitted at</option>
              <option value="session_date">session date</option>
              <option value="id">id</option>
              <option value="instructor_id">instructor</option>
              <option value="supervisor_id">supervisor</option>
            </select>
            <select value={filters.sort_dir}
              onChange={(e) => setFilters((p) => ({ ...p, sort_dir: e.target.value }))}>
              <option value="desc">newest first</option>
              <option value="asc">oldest first</option>
            </select>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                border: "1.5px solid #bbd6ea",
                borderRadius: 8,
                padding: "0 8px",
                background: "white",
                minHeight: 40,
                gridColumn: "span 2",
              }}
            >
              <input
                type={filters.date_from ? "date" : "text"}
                placeholder="Start Date"
                value={filters.date_from}
                onChange={(e) => setFilters((p) => ({ ...p, date_from: e.target.value }))}
                onFocus={(e) => { e.currentTarget.type = "date"; }}
                onBlur={(e) => {
                  if (!e.currentTarget.value) e.currentTarget.type = "text";
                }}
                style={{ border: "none", boxShadow: "none", padding: "8px 4px", minWidth: 130 }}
              />
              <input
                type={filters.date_to ? "date" : "text"}
                placeholder="End Date"
                value={filters.date_to}
                onChange={(e) => setFilters((p) => ({ ...p, date_to: e.target.value }))}
                onFocus={(e) => { e.currentTarget.type = "date"; }}
                onBlur={(e) => {
                  if (!e.currentTarget.value) e.currentTarget.type = "text";
                }}
                style={{ border: "none", boxShadow: "none", padding: "8px 4px", minWidth: 130 }}
              />
            </div>
            <button type="submit">Apply Filters</button>
          </form>
          <a href={exportEvaluationsCsvUrl()} target="_blank" rel="noreferrer" className="button-link"
            onClick={(e) => { if (!token) return; e.preventDefault(); downloadCsv(); }}>
            Export CSV
          </a>
          <EvaluationTable rows={evaluations} onView={handleViewReport} onEdit={handleEditEval} />
          <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 8, marginTop: 12 }}>
            <button
              type="button"
              className="btn-add"
              disabled={evaluationsPage === 0}
              onClick={() => {
                const nextPage = Math.max(0, evaluationsPage - 1);
                setEvaluationsPage(nextPage);
                setAppliedQuery((prev) => ({ ...prev, limit: EVALUATIONS_PAGE_SIZE, offset: nextPage * EVALUATIONS_PAGE_SIZE }));
              }}
            >
              Previous
            </button>
            <span style={{ fontSize: 13, color: "#64748b" }}>Page {evaluationsPage + 1}</span>
            <button
              type="button"
              className="btn-add"
              disabled={evaluations.length < EVALUATIONS_PAGE_SIZE}
              onClick={() => {
                const nextPage = evaluationsPage + 1;
                setEvaluationsPage(nextPage);
                setAppliedQuery((prev) => ({ ...prev, limit: EVALUATIONS_PAGE_SIZE, offset: nextPage * EVALUATIONS_PAGE_SIZE }));
              }}
            >
              Next
            </button>
          </div>
        </Section>
      )}

      {reportEval && (
        <EvaluationReportModal evaluation={reportEval} onClose={() => setReportEval(null)} />
      )}

      {editEval && token && (
        <EvaluationEditModal
          token={token}
          evaluation={editEval}
          updateFn={updateManagerEvaluation}
          showSubmit={false}
          onSaved={(updated) => {
            setEvaluations((prev) => prev.map((e) => (e.id === updated.id ? { ...e } : e)));
            setEditEval(null);
          }}
          onSubmitted={() => setEditEval(null)}
          onClose={() => setEditEval(null)}
        />
      )}
    </>
  );
}

/* ---- Sub-components ---- */

function ManagerUsers({
  token,
  users,
  onCreated,
  onUpdated,
  onDeleted,
}: {
  token: string;
  users: User[];
  onCreated: (u: User) => void;
  onUpdated: (u: User) => void;
  onDeleted: (id: number) => void;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("INSTRUCTOR");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editPhone, setEditPhone] = useState("");
  const [editRole, setEditRole] = useState<UserRole>("INSTRUCTOR");
  const [editActive, setEditActive] = useState(true);
  const [editPassword, setEditPassword] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      setError("");
      const user = await createUser(token, {
        name,
        email,
        phone: phone.trim() || null,
        password,
        role,
        active: true,
      });
      onCreated(user);
      setName("");
      setEmail("");
      setPhone("");
      setPassword("");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  function beginEdit(user: User) {
    setEditingId(user.id);
    setEditName(user.name);
    setEditEmail(user.email);
    setEditPhone(user.phone ?? "");
    setEditRole(user.role);
    setEditActive(user.active);
    setEditPassword("");
    setError("");
  }

  function cancelEdit() {
    setEditingId(null);
    setEditPassword("");
  }

  async function saveEdit(userId: number) {
    try {
      setError("");
      const payload: {
        name: string;
        email: string;
        phone: string | null;
        role: UserRole;
        active: boolean;
        password?: string;
      } = {
        name: editName,
        email: editEmail,
        phone: editPhone.trim() || null,
        role: editRole,
        active: editActive,
      };
      if (editPassword.trim()) payload.password = editPassword.trim();
      const updated = await updateUser(token, userId, payload);
      onUpdated(updated);
      cancelEdit();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function removeUser(user: User) {
    const confirmed = window.confirm(`Delete user ${user.name}?`);
    if (!confirmed) return;
    try {
      setError("");
      await deleteUser(token, user.id);
      onDeleted(user.id);
      if (editingId === user.id) cancelEdit();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const instructors = users.filter((u) => u.role === "INSTRUCTOR");
  const supervisors = users.filter((u) => u.role === "SUPERVISOR");
  const managers = users.filter((u) => u.role === "MANAGER");

  return (
    <Section title="Users">
      <form className="form inline" onSubmit={onSubmit}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Full name" required />
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" type="email" required />
        <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Phone (optional)" />
        <input value={password} onChange={(e) => setPassword(e.target.value)}
          placeholder="Password (8+ chars)" minLength={8} type="password" required />
        <select value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
          <option value="MANAGER">Manager</option>
          <option value="SUPERVISOR">Supervisor</option>
          <option value="INSTRUCTOR">Instructor</option>
        </select>
        <button type="submit">Add User</button>
      </form>
      {error && <p className="error">{error}</p>}

      {[{ label: "Instructors", list: instructors }, { label: "Supervisors", list: supervisors }, { label: "Managers", list: managers }].map(({ label, list }) => (
        list.length > 0 && (
          <div key={label} style={{ marginBottom: 20 }}>
            <p className="chart-section-title">{label} ({list.length})</p>
            <table>
              <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Role</th><th>Active</th><th>Actions</th></tr></thead>
              <tbody>
                {list.map((u) => (
                  <tr key={u.id}>
                    {editingId === u.id ? (
                      <>
                        <td><input value={editName} onChange={(e) => setEditName(e.target.value)} /></td>
                        <td><input type="email" value={editEmail} onChange={(e) => setEditEmail(e.target.value)} /></td>
                        <td><input value={editPhone} onChange={(e) => setEditPhone(e.target.value)} /></td>
                        <td>
                          <select value={editRole} onChange={(e) => setEditRole(e.target.value as UserRole)}>
                            <option value="MANAGER">Manager</option>
                            <option value="SUPERVISOR">Supervisor</option>
                            <option value="INSTRUCTOR">Instructor</option>
                          </select>
                        </td>
                        <td>
                          <label style={{ flexDirection: "row", alignItems: "center", gap: 6, fontWeight: 400 }}>
                            <input
                              type="checkbox"
                              checked={editActive}
                              onChange={(e) => setEditActive(e.target.checked)}
                              style={{ width: "auto" }}
                            />
                            Active
                          </label>
                        </td>
                        <td>
                          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                            <input
                              type="password"
                              value={editPassword}
                              onChange={(e) => setEditPassword(e.target.value)}
                              minLength={8}
                              placeholder="New password (optional)"
                              style={{ minWidth: 180 }}
                            />
                            <button type="button" onClick={() => saveEdit(u.id)}>Save</button>
                            <button type="button" className="btn-add" onClick={cancelEdit}>Cancel</button>
                          </div>
                        </td>
                      </>
                    ) : (
                      <>
                        <td>{u.name}</td>
                        <td>{u.email}</td>
                        <td>{u.phone || "-"}</td>
                        <td>{u.role}</td>
                        <td>{u.active ? "Yes" : "No"}</td>
                        <td>
                          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                            <button type="button" onClick={() => beginEdit(u)}>Edit</button>
                            <button type="button" className="btn-add" onClick={() => removeUser(u)}>Delete</button>
                          </div>
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ))}
    </Section>
  );
}

function ManagerLevels({
  token,
  levels,
  skills,
  onLevelCreated,
  onLevelUpdated,
  onLevelDeleted,
  onSkillCreated,
  onSkillUpdated,
  onSkillDeleted,
}: {
  token: string;
  levels: Level[];
  skills: Skill[];
  onLevelCreated: (l: Level) => void;
  onLevelUpdated: (l: Level) => void;
  onLevelDeleted: (levelId: number) => void;
  onSkillCreated: (s: Skill) => void;
  onSkillUpdated: (s: Skill) => void;
  onSkillDeleted: (skillId: number) => void;
}) {
  const [levelName, setLevelName] = useState("");
  const [editingLevelId, setEditingLevelId] = useState<number | null>(null);
  const [editLevelName, setEditLevelName] = useState("");
  const [editLevelActive, setEditLevelActive] = useState(true);

  const [skillName, setSkillName] = useState("");
  const [skillDescription, setSkillDescription] = useState("");
  const [skillLevelId, setSkillLevelId] = useState<number>(levels[0]?.id ?? 0);
  const [editingSkillId, setEditingSkillId] = useState<number | null>(null);
  const [editSkillName, setEditSkillName] = useState("");
  const [editSkillDescription, setEditSkillDescription] = useState("");
  const [editSkillLevelId, setEditSkillLevelId] = useState<number>(levels[0]?.id ?? 0);
  const [editSkillActive, setEditSkillActive] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!skillLevelId && levels.length > 0) setSkillLevelId(levels[0].id);
  }, [skillLevelId, levels]);

  async function onCreateLevel(e: FormEvent) {
    e.preventDefault();
    try {
      setError("");
      const level = await createLevel(token, { name: levelName, active: true });
      onLevelCreated(level);
      setLevelName("");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  function beginEditLevel(level: Level) {
    setEditingLevelId(level.id);
    setEditLevelName(level.name);
    setEditLevelActive(level.active);
    setError("");
  }

  async function saveLevel(levelId: number) {
    try {
      setError("");
      const updated = await updateLevel(token, levelId, { name: editLevelName, active: editLevelActive });
      onLevelUpdated(updated);
      setEditingLevelId(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function removeLevel(level: Level) {
    const confirmed = window.confirm(`Delete level ${level.name}?`);
    if (!confirmed) return;
    try {
      setError("");
      await deleteLevel(token, level.id);
      onLevelDeleted(level.id);
      if (editingLevelId === level.id) setEditingLevelId(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onCreateSkill(e: FormEvent) {
    e.preventDefault();
    try {
      setError("");
      const skill = await createSkill(token, {
        name: skillName,
        description: skillDescription.trim() || undefined,
        level_id: skillLevelId,
        active: true,
      });
      onSkillCreated(skill);
      setSkillName("");
      setSkillDescription("");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  function beginEditSkill(skill: Skill) {
    setEditingSkillId(skill.id);
    setEditSkillName(skill.name);
    setEditSkillDescription(skill.description ?? "");
    setEditSkillLevelId(skill.level_id);
    setEditSkillActive(skill.active);
    setError("");
  }

  async function saveSkill(skillId: number) {
    try {
      setError("");
      const updated = await updateSkill(token, skillId, {
        name: editSkillName,
        description: editSkillDescription.trim() || null,
        level_id: editSkillLevelId,
        active: editSkillActive,
      });
      onSkillUpdated(updated);
      setEditingSkillId(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function removeSkill(skill: Skill) {
    const confirmed = window.confirm(`Delete skill ${skill.name}?`);
    if (!confirmed) return;
    try {
      setError("");
      await deleteSkill(token, skill.id);
      onSkillDeleted(skill.id);
      if (editingSkillId === skill.id) setEditingSkillId(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <Section title="Levels">
      <form className="form inline" onSubmit={onCreateLevel}>
        <input
          value={levelName}
          onChange={(e) => setLevelName(e.target.value)}
          placeholder="e.g. Level 1 - Beginner"
          required
        />
        <button type="submit">Add Level</button>
      </form>

      <table>
        <thead><tr><th>Level Name</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>
          {levels.map((l) => (
            <tr key={l.id}>
              {editingLevelId === l.id ? (
                <>
                  <td><input value={editLevelName} onChange={(e) => setEditLevelName(e.target.value)} /></td>
                  <td>
                    <label style={{ flexDirection: "row", alignItems: "center", gap: 6, fontWeight: 400 }}>
                      <input
                        type="checkbox"
                        checked={editLevelActive}
                        onChange={(e) => setEditLevelActive(e.target.checked)}
                        style={{ width: "auto" }}
                      />
                      Active
                    </label>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      <button type="button" onClick={() => saveLevel(l.id)}>Save</button>
                      <button type="button" className="btn-add" onClick={() => setEditingLevelId(null)}>Cancel</button>
                    </div>
                  </td>
                </>
              ) : (
                <>
                  <td>{l.name}</td>
                  <td>
                    <span className={l.active ? "badge-submitted" : "badge-draft"}>{l.active ? "Active" : "Inactive"}</span>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      <button type="button" onClick={() => beginEditLevel(l)}>Edit</button>
                      <button type="button" className="btn-add" onClick={() => removeLevel(l)}>Delete</button>
                    </div>
                  </td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ marginTop: 20 }}>
        <p className="chart-section-title">Skills</p>
        <form className="form inline" onSubmit={onCreateSkill}>
          <input value={skillName} onChange={(e) => setSkillName(e.target.value)} placeholder="e.g. Freestyle" required />
          <input value={skillDescription} onChange={(e) => setSkillDescription(e.target.value)} placeholder="Description" />
          <select value={skillLevelId} onChange={(e) => setSkillLevelId(Number(e.target.value))}>
            {levels.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
          </select>
          <button type="submit" disabled={levels.length === 0}>Add Skill</button>
        </form>
      </div>

      <table>
        <thead><tr><th>Skill</th><th>Level</th><th>Description</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>
          {skills.map((s) => (
            <tr key={s.id}>
              {editingSkillId === s.id ? (
                <>
                  <td><input value={editSkillName} onChange={(e) => setEditSkillName(e.target.value)} /></td>
                  <td>
                    <select value={editSkillLevelId} onChange={(e) => setEditSkillLevelId(Number(e.target.value))}>
                      {levels.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                    </select>
                  </td>
                  <td><input value={editSkillDescription} onChange={(e) => setEditSkillDescription(e.target.value)} /></td>
                  <td>
                    <label style={{ flexDirection: "row", alignItems: "center", gap: 6, fontWeight: 400 }}>
                      <input
                        type="checkbox"
                        checked={editSkillActive}
                        onChange={(e) => setEditSkillActive(e.target.checked)}
                        style={{ width: "auto" }}
                      />
                      Active
                    </label>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      <button type="button" onClick={() => saveSkill(s.id)}>Save</button>
                      <button type="button" className="btn-add" onClick={() => setEditingSkillId(null)}>Cancel</button>
                    </div>
                  </td>
                </>
              ) : (
                <>
                  <td>{s.name}</td>
                  <td>{levels.find((l) => l.id === s.level_id)?.name ?? s.level_id}</td>
                  <td style={{ color: "#64748b" }}>{s.description ?? "-"}</td>
                  <td>
                    <span className={s.active ? "badge-submitted" : "badge-draft"}>{s.active ? "Active" : "Inactive"}</span>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      <button type="button" onClick={() => beginEditSkill(s)}>Edit</button>
                      <button type="button" className="btn-add" onClick={() => removeSkill(s)}>Delete</button>
                    </div>
                  </td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      {error && <p className="error" style={{ marginTop: 10 }}>{error}</p>}
    </Section>
  );
}


function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="stat-card">
      <div className="stat-card-value" style={{ color }}>{value}</div>
      <div className="stat-card-label">{label}</div>
    </div>
  );
}

function monthLabel(dateStr: string) {
  return new Date(dateStr + "T00:00:00").toLocaleDateString("en-US", { month: "short", year: "2-digit" });
}

function ManagerDashboard({
  rows, onGo, onExportCsv, onEmailCsv, appliedManagerQuery, onView, onEdit
}: {
  rows: EvaluationSummary[];
  onGo: (tab: ManagerTab) => void;
  onExportCsv: () => void;
  onEmailCsv: (payload: { to: string[]; subject?: string; message?: string; filters?: ManagerEvaluationQuery }) => Promise<void>;
  appliedManagerQuery: ManagerEvaluationQuery;
  onView?: (id: number) => void;
  onEdit?: (id: number) => void;
}) {
  const { total, submitted, recent7d, recent } = useMemo(() => {
    const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    let submitted = 0, recent7d = 0;
    for (const r of rows) {
      if (r.status === "SUBMITTED") submitted++;
      if (r.session_date && new Date(r.session_date) >= weekAgo) recent7d++;
    }
    return { total: rows.length, submitted, recent7d, recent: rows.slice(0, 8) };
  }, [rows]);

  // Instructor performance chart
  const instructorData = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const r of rows) {
      counts[r.instructor_name] = (counts[r.instructor_name] ?? 0) + 1;
    }
    return Object.entries(counts)
      .sort(([, a], [, b]) => b - a)
      .map(([label, value]) => ({ label, value, color: "#0077b6" }));
  }, [rows]);

  // Skill distribution
  const skillData = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const r of rows) {
      counts[r.skill_name] = (counts[r.skill_name] ?? 0) + 1;
    }
    return Object.entries(counts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 8)
      .map(([label, value]) => ({ label, value, color: "#0096c7" }));
  }, [rows]);

  // Monthly trend
  const monthlyData = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const r of rows) {
      if (r.session_date) {
        const key = r.session_date.slice(0, 7);
        counts[key] = (counts[key] ?? 0) + 1;
      }
    }
    return Object.entries(counts)
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-6)
      .map(([month, value]) => ({ label: monthLabel(month + "-01"), value, color: "#0f9b8e" }));
  }, [rows]);

  const [showEmail, setShowEmail] = useState(false);
  const [toText, setToText] = useState("");
  const [subject, setSubject] = useState("Propel Swim School — Evaluation Export");
  const [message, setMessage] = useState("");
  const [useCurrentFilters, setUseCurrentFilters] = useState(false);
  const [sending, setSending] = useState(false);
  const [emailStatus, setEmailStatus] = useState("");

  async function onSubmitEmail(e: FormEvent) {
    e.preventDefault();
    const recipients = toText.split(",").map((x) => x.trim()).filter(Boolean);
    if (recipients.length === 0) { setEmailStatus("At least one recipient is required."); return; }
    setSending(true); setEmailStatus("");
    try {
      await onEmailCsv({
        to: recipients,
        subject: subject.trim() || "Propel Swim School — Evaluation Export",
        message: message.trim() || undefined,
        filters: useCurrentFilters ? appliedManagerQuery : undefined,
      });
      setEmailStatus("Email sent."); setToText(""); setMessage(""); setUseCurrentFilters(false);
    } catch (err) {
      setEmailStatus((err as Error).message);
    } finally { setSending(false); }
  }

  return (
    <>
      {/* Stat cards */}
      <div className="stat-cards">
        <StatCard label="Total Evaluations" value={total} color="#023e8a" />
        <StatCard label="Submitted" value={submitted} color="#0077b6" />
        <StatCard label="Sessions This Week" value={recent7d} color="#0f9b8e" />
      </div>

      {/* Quick actions */}
      <div className="card" style={{ padding: "16px 24px" }}>
        <div className="dash-actions">
          <button onClick={() => onGo("users")}>👤 Manage Users</button>
          <button onClick={() => onGo("levels")}>🌊 Levels</button>
          <button onClick={() => onGo("evaluations")}>📊 All Evaluations</button>
          <button onClick={onExportCsv}>⬇ Export CSV</button>
          <button onClick={() => setShowEmail((p) => !p)}>
            {showEmail ? "✕ Close Email" : "✉ Email CSV"}
          </button>
        </div>
        {showEmail && (
          <form className="form" onSubmit={onSubmitEmail} style={{ marginTop: 16, marginBottom: 0 }}>
            <label>
              To (comma-separated)
              <input value={toText} onChange={(e) => setToText(e.target.value)} placeholder="coach@propelswim.com" required />
            </label>
            <label>
              Subject
              <input value={subject} onChange={(e) => setSubject(e.target.value)} />
            </label>
            <label>
              Message
              <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={3} />
            </label>
            <label style={{ flexDirection: "row", alignItems: "center", gap: 8, fontWeight: 400 }}>
              <input type="checkbox" checked={useCurrentFilters} onChange={(e) => setUseCurrentFilters(e.target.checked)} style={{ width: "auto" }} />
              Use current filters from All Evaluations
            </label>
            <button type="submit" disabled={sending}>{sending ? "Sending..." : "Send"}</button>
            {emailStatus && <p className={emailStatus === "Email sent." ? "" : "error"}>{emailStatus}</p>}
          </form>
        )}
      </div>

      {/* Charts: status donut + monthly trend */}
      <div className="two-col">
        <div className="card">
          <h2>Status Distribution</h2>
          <DonutChart submitted={submitted} total={total} />
        </div>

        <div className="card">
          <h2>Monthly Volume</h2>
          {monthlyData.length > 0 ? (
            <BarChart data={monthlyData} labelWidth={80} />
          ) : (
            <p style={{ color: "#64748b", fontSize: 14 }}>No session data yet.</p>
          )}
        </div>
      </div>

      {/* Charts: instructor performance + skill breakdown */}
      <div className="two-col">
        <div className="card">
          <h2>Instructor Performance</h2>
          <p className="chart-section-title">Total evaluations per instructor</p>
          {instructorData.length > 0 ? (
            <BarChart data={instructorData} />
          ) : (
            <p style={{ color: "#64748b", fontSize: 14 }}>No data yet.</p>
          )}
        </div>

        <div className="card">
          <h2>Stroke & Skill Breakdown</h2>
          <p className="chart-section-title">Evaluations by skill area</p>
          {skillData.length > 0 ? (
            <BarChart data={skillData} />
          ) : (
            <p style={{ color: "#64748b", fontSize: 14 }}>No data yet.</p>
          )}
        </div>
      </div>

      {/* Recent evaluations */}
      <div className="card">
        <h2>Recent Evaluations</h2>
        {recent.length > 0 ? (
          <EvaluationTable rows={recent} onView={onView} onEdit={onEdit} />
        ) : (
          <p style={{ color: "#64748b", fontSize: 14 }}>No evaluations yet.</p>
        )}
      </div>
    </>
  );
}



