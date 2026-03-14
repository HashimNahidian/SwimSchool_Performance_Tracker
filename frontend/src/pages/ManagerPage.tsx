import { FormEvent, useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth";
import type { ManagerEvaluationQuery } from "../api";
import {
  createAttribute,
  createLevel,
  createSkill,
  createUser,
  deleteAttribute,
  deleteLevel,
  deleteSkill,
  deleteUser,
  emailEvaluationsCsv,
  exportEvaluationsCsvUrl,
  getManagerEvaluationDetail,
  listAttributes,
  listLevels,
  listManagerEvaluationsWithQuery,
  listSkills,
  listUsers,
  updateAttribute,
  updateLevel,
  updateManagerEvaluation,
  updateSkill,
  updateUser,
} from "../api";
import type { Attribute, EvaluationDetail, EvaluationSummary, Level, Skill, User, UserRole } from "../types";
import { Section } from "../components/Section";
import { EvaluationTable } from "../components/EvaluationTable";
import { BarChart } from "../components/BarChart";
import { EvaluationReportModal } from "../components/EvaluationReport";
import { EvaluationEditModal } from "../components/EvaluationEditModal";

type ManagerTab = "dashboard" | "users" | "levels" | "evaluations";

const MANAGER_TABS: ManagerTab[] = ["dashboard", "users", "levels", "evaluations"];

const SORT_FIELDS = new Set<NonNullable<ManagerEvaluationQuery["sort_by"]>>([
  "id", "created_at", "updated_at", "instructor_id", "supervisor_id", "skill_id", "final_grade"
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
  const skillId = parsePositiveInt(filters.skill_id);
  const finalGrade = parsePositiveInt(filters.final_grade);
  if (instructorId !== undefined) q.instructor_id = instructorId;
  if (supervisorId !== undefined) q.supervisor_id = supervisorId;
  if (skillId !== undefined) q.skill_id = skillId;
  if (finalGrade !== undefined) q.final_grade = finalGrade;
  if (filters.date_from) q.date_from = filters.date_from;
  if (filters.date_to) q.date_to = filters.date_to;
  q.sort_by = SORT_FIELDS.has(filters.sort_by as NonNullable<ManagerEvaluationQuery["sort_by"]>)
    ? (filters.sort_by as NonNullable<ManagerEvaluationQuery["sort_by"]>)
    : "created_at";
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
  const [attributes, setAttributes] = useState<Attribute[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationSummary[]>([]);
  const [reportEval, setReportEval] = useState<EvaluationDetail | null>(null);
  const [editEval, setEditEval] = useState<EvaluationDetail | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [filters, setFilters] = useState({
    instructor_id: "", supervisor_id: "", skill_id: "",
    final_grade: "", date_from: "", date_to: "",
    sort_by: "created_at", sort_dir: "desc"
  });
  const [appliedQuery, setAppliedQuery] = useState<ManagerEvaluationQuery>({
    sort_by: "created_at", sort_dir: "desc", limit: EVALUATIONS_PAGE_SIZE, offset: 0
  });
  const [evaluationsPage, setEvaluationsPage] = useState(0);

  useEffect(() => {
    if (!token) return;
    Promise.all([
      listUsers(token), listLevels(token), listSkills(token), listAttributes(token),
      listManagerEvaluationsWithQuery(token, appliedQuery)
    ])
      .then(([u, l, s, a, e]) => {
        setUsers(u);
        setLevels(l);
        setSkills(s);
        setAttributes(a);
        setEvaluations(e);
      })
      .catch((e: Error) => setError(e.message));
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
          attributes={attributes}
          onLevelCreated={(l) => setLevels((p) => [...p, l])}
          onLevelUpdated={(l) => setLevels((p) => p.map((item) => (item.id === l.id ? l : item)))}
          onLevelDeleted={(levelId) => {
            setLevels((p) => p.filter((item) => item.id !== levelId));
            setSkills((p) => p.filter((item) => item.level_id !== levelId));
          }}
          onSkillCreated={(s) => setSkills((p) => [...p, s])}
          onSkillUpdated={(s) => setSkills((p) => p.map((item) => (item.id === s.id ? s : item)))}
          onSkillDeleted={(skillId) => setSkills((p) => p.filter((item) => item.id !== skillId))}
          onAttributeCreated={(a) => setAttributes((p) => [...p, a])}
          onAttributeUpdated={(a) => setAttributes((p) => p.map((item) => (item.id === a.id ? a : item)))}
          onAttributeDeleted={(id) => setAttributes((p) => p.filter((item) => item.id !== id))}
        />
      )}
      {tab === "evaluations" && (
        <Section title={`All Evaluations${loadingReport ? " — Loading report…" : ""}`}>
          <form className="form inline" onSubmit={(e) => { e.preventDefault(); setEvaluationsPage(0); setAppliedQuery({ ...buildQuery(filters), limit: EVALUATIONS_PAGE_SIZE, offset: 0 }); }}>
            <input placeholder="instructor id" value={filters.instructor_id}
              onChange={(e) => setFilters((p) => ({ ...p, instructor_id: e.target.value }))} />
            <input placeholder="supervisor id" value={filters.supervisor_id}
              onChange={(e) => setFilters((p) => ({ ...p, supervisor_id: e.target.value }))} />
            <select value={filters.skill_id}
              onChange={(e) => setFilters((p) => ({ ...p, skill_id: e.target.value }))}>
              <option value="">all skills</option>
              {skills.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <select value={filters.final_grade}
              onChange={(e) => setFilters((p) => ({ ...p, final_grade: e.target.value }))}>
              <option value="">all grades</option>
              <option value="1">1 — Remediate</option>
              <option value="2">2 — Meets</option>
              <option value="3">3 — Exceeds</option>
            </select>
            <select value={filters.sort_by}
              onChange={(e) => setFilters((p) => ({ ...p, sort_by: e.target.value }))}>
              <option value="created_at">date created</option>
              <option value="updated_at">date updated</option>
              <option value="final_grade">final grade</option>
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
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("INSTRUCTOR");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editFullName, setEditFullName] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editPhone, setEditPhone] = useState("");
  const [editRole, setEditRole] = useState<UserRole>("INSTRUCTOR");
  const [editIsActive, setEditIsActive] = useState(true);
  const [editPassword, setEditPassword] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      setError("");
      const user = await createUser(token, {
        full_name: fullName,
        email,
        phone: phone.trim() || null,
        password,
        role,
        is_active: true,
      });
      onCreated(user);
      setFullName("");
      setEmail("");
      setPhone("");
      setPassword("");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  function beginEdit(user: User) {
    setEditingId(user.id);
    setEditFullName(user.full_name);
    setEditEmail(user.email);
    setEditPhone(user.phone ?? "");
    setEditRole(user.role);
    setEditIsActive(user.is_active);
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
        full_name: string;
        email: string;
        phone: string | null;
        role: UserRole;
        is_active: boolean;
        password?: string;
      } = {
        full_name: editFullName,
        email: editEmail,
        phone: editPhone.trim() || null,
        role: editRole,
        is_active: editIsActive,
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
    const confirmed = window.confirm(`Delete user ${user.full_name}?`);
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
        <input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Full name" required />
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
                        <td><input value={editFullName} onChange={(e) => setEditFullName(e.target.value)} /></td>
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
                              checked={editIsActive}
                              onChange={(e) => setEditIsActive(e.target.checked)}
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
                        <td>{u.full_name}</td>
                        <td>{u.email}</td>
                        <td>{u.phone || "-"}</td>
                        <td>{u.role}</td>
                        <td>{u.is_active ? "Yes" : "No"}</td>
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

type LevelsSubTab = "levels" | "skills" | "attributes";

function ManagerLevels({
  token,
  levels,
  skills,
  attributes,
  onLevelCreated,
  onLevelUpdated,
  onLevelDeleted,
  onSkillCreated,
  onSkillUpdated,
  onSkillDeleted,
  onAttributeCreated,
  onAttributeUpdated,
  onAttributeDeleted,
}: {
  token: string;
  levels: Level[];
  skills: Skill[];
  attributes: Attribute[];
  onLevelCreated: (l: Level) => void;
  onLevelUpdated: (l: Level) => void;
  onLevelDeleted: (levelId: number) => void;
  onSkillCreated: (s: Skill) => void;
  onSkillUpdated: (s: Skill) => void;
  onSkillDeleted: (skillId: number) => void;
  onAttributeCreated: (a: Attribute) => void;
  onAttributeUpdated: (a: Attribute) => void;
  onAttributeDeleted: (id: number) => void;
}) {
  const [subTab, setSubTab] = useState<LevelsSubTab>("levels");

  // ── Levels state ──
  const [levelName, setLevelName] = useState("");
  const [editingLevelId, setEditingLevelId] = useState<number | null>(null);
  const [editLevelName, setEditLevelName] = useState("");

  // ── Skills state ──
  const [skillName, setSkillName] = useState("");
  const [skillLevelId, setSkillLevelId] = useState<number>(levels[0]?.id ?? 0);
  const [editingSkillId, setEditingSkillId] = useState<number | null>(null);
  const [editSkillName, setEditSkillName] = useState("");
  const [editSkillLevelId, setEditSkillLevelId] = useState<number>(levels[0]?.id ?? 0);

  // ── Attributes state ──
  const [attrName, setAttrName] = useState("");
  const [attrDesc, setAttrDesc] = useState("");
  const [editingAttrId, setEditingAttrId] = useState<number | null>(null);
  const [editAttrName, setEditAttrName] = useState("");
  const [editAttrDesc, setEditAttrDesc] = useState("");

  const [error, setError] = useState("");

  useEffect(() => {
    if (!skillLevelId && levels.length > 0) setSkillLevelId(levels[0].id);
  }, [skillLevelId, levels]);

  // ── Level handlers ──
  async function onCreateLevel(e: FormEvent) {
    e.preventDefault();
    try {
      setError("");
      const level = await createLevel(token, { name: levelName });
      onLevelCreated(level);
      setLevelName("");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function saveLevel(levelId: number) {
    try {
      setError("");
      const updated = await updateLevel(token, levelId, { name: editLevelName });
      onLevelUpdated(updated);
      setEditingLevelId(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function removeLevel(level: Level) {
    if (!window.confirm(`Delete level "${level.name}"? All its skills will also be deleted.`)) return;
    try {
      setError("");
      await deleteLevel(token, level.id);
      onLevelDeleted(level.id);
      if (editingLevelId === level.id) setEditingLevelId(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  // ── Skill handlers ──
  async function onCreateSkill(e: FormEvent) {
    e.preventDefault();
    try {
      setError("");
      const skill = await createSkill(token, { name: skillName, level_id: skillLevelId });
      onSkillCreated(skill);
      setSkillName("");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function saveSkill(skillId: number) {
    try {
      setError("");
      const updated = await updateSkill(token, skillId, { name: editSkillName, level_id: editSkillLevelId });
      onSkillUpdated(updated);
      setEditingSkillId(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function removeSkill(skill: Skill) {
    if (!window.confirm(`Delete skill "${skill.name}"?`)) return;
    try {
      setError("");
      await deleteSkill(token, skill.id);
      onSkillDeleted(skill.id);
      if (editingSkillId === skill.id) setEditingSkillId(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  // ── Attribute handlers ──
  async function onCreateAttribute(e: FormEvent) {
    e.preventDefault();
    try {
      setError("");
      const attr = await createAttribute(token, { name: attrName, description: attrDesc.trim() || null });
      onAttributeCreated(attr);
      setAttrName("");
      setAttrDesc("");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function saveAttribute(attrId: number) {
    try {
      setError("");
      const updated = await updateAttribute(token, attrId, {
        name: editAttrName,
        description: editAttrDesc.trim() || null,
      });
      onAttributeUpdated(updated);
      setEditingAttrId(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function removeAttribute(attr: Attribute) {
    if (!window.confirm(`Delete attribute "${attr.name}"?`)) return;
    try {
      setError("");
      await deleteAttribute(token, attr.id);
      onAttributeDeleted(attr.id);
      if (editingAttrId === attr.id) setEditingAttrId(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <Section title="Curriculum">
      <nav className="tabs" style={{ marginBottom: 16 }}>
        {(["levels", "skills", "attributes"] as LevelsSubTab[]).map((t) => (
          <button key={t} className={subTab === t ? "active" : ""} onClick={() => { setSubTab(t); setError(""); }}>
            {t === "levels" ? "Levels" : t === "skills" ? "Skills" : "Attributes"}
          </button>
        ))}
      </nav>

      {error && <p className="error" style={{ marginBottom: 10 }}>{error}</p>}

      {subTab === "levels" && (
        <>
          <form className="form inline" onSubmit={onCreateLevel}>
            <input value={levelName} onChange={(e) => setLevelName(e.target.value)} placeholder="e.g. Seahorse" required />
            <button type="submit">Add Level</button>
          </form>
          <table>
            <thead><tr><th>Level Name</th><th>Skills</th><th>Actions</th></tr></thead>
            <tbody>
              {levels.map((l) => (
                <tr key={l.id}>
                  {editingLevelId === l.id ? (
                    <>
                      <td><input value={editLevelName} onChange={(e) => setEditLevelName(e.target.value)} /></td>
                      <td>{skills.filter((s) => s.level_id === l.id).length}</td>
                      <td>
                        <div style={{ display: "flex", gap: 8 }}>
                          <button type="button" onClick={() => saveLevel(l.id)}>Save</button>
                          <button type="button" className="btn-add" onClick={() => setEditingLevelId(null)}>Cancel</button>
                        </div>
                      </td>
                    </>
                  ) : (
                    <>
                      <td>{l.name}</td>
                      <td>{skills.filter((s) => s.level_id === l.id).length}</td>
                      <td>
                        <div style={{ display: "flex", gap: 8 }}>
                          <button type="button" onClick={() => { setEditingLevelId(l.id); setEditLevelName(l.name); setError(""); }}>Edit</button>
                          <button type="button" className="btn-add" onClick={() => removeLevel(l)}>Delete</button>
                        </div>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {subTab === "skills" && (
        <>
          <form className="form inline" onSubmit={onCreateSkill}>
            <input value={skillName} onChange={(e) => setSkillName(e.target.value)} placeholder="e.g. Freestyle" required />
            <select value={skillLevelId} onChange={(e) => setSkillLevelId(Number(e.target.value))}>
              {levels.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
            <button type="submit" disabled={levels.length === 0}>Add Skill</button>
          </form>
          <table>
            <thead><tr><th>Skill</th><th>Level</th><th>Actions</th></tr></thead>
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
                      <td>
                        <div style={{ display: "flex", gap: 8 }}>
                          <button type="button" onClick={() => saveSkill(s.id)}>Save</button>
                          <button type="button" className="btn-add" onClick={() => setEditingSkillId(null)}>Cancel</button>
                        </div>
                      </td>
                    </>
                  ) : (
                    <>
                      <td>{s.name}</td>
                      <td>{levels.find((l) => l.id === s.level_id)?.name ?? s.level_id}</td>
                      <td>
                        <div style={{ display: "flex", gap: 8 }}>
                          <button type="button" onClick={() => { setEditingSkillId(s.id); setEditSkillName(s.name); setEditSkillLevelId(s.level_id); setError(""); }}>Edit</button>
                          <button type="button" className="btn-add" onClick={() => removeSkill(s)}>Delete</button>
                        </div>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {subTab === "attributes" && (
        <>
          <form className="form inline" onSubmit={onCreateAttribute}>
            <input value={attrName} onChange={(e) => setAttrName(e.target.value)} placeholder="Attribute name" required />
            <input value={attrDesc} onChange={(e) => setAttrDesc(e.target.value)} placeholder="Description (optional)" />
            <button type="submit">Add Attribute</button>
          </form>
          <table>
            <thead><tr><th>Name</th><th>Description</th><th>Actions</th></tr></thead>
            <tbody>
              {attributes.map((a) => (
                <tr key={a.id}>
                  {editingAttrId === a.id ? (
                    <>
                      <td><input value={editAttrName} onChange={(e) => setEditAttrName(e.target.value)} /></td>
                      <td><input value={editAttrDesc} onChange={(e) => setEditAttrDesc(e.target.value)} placeholder="Description (optional)" /></td>
                      <td>
                        <div style={{ display: "flex", gap: 8 }}>
                          <button type="button" onClick={() => saveAttribute(a.id)}>Save</button>
                          <button type="button" className="btn-add" onClick={() => setEditingAttrId(null)}>Cancel</button>
                        </div>
                      </td>
                    </>
                  ) : (
                    <>
                      <td>{a.name}</td>
                      <td style={{ color: "#64748b", fontSize: 13 }}>{a.description ?? "—"}</td>
                      <td>
                        <div style={{ display: "flex", gap: 8 }}>
                          <button type="button" onClick={() => { setEditingAttrId(a.id); setEditAttrName(a.name); setEditAttrDesc(a.description ?? ""); setError(""); }}>Edit</button>
                          <button type="button" className="btn-add" onClick={() => removeAttribute(a)}>Delete</button>
                        </div>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
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
  const { total, graded, recent7d, recent } = useMemo(() => {
    const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    let graded = 0, recent7d = 0;
    for (const r of rows) {
      if (r.final_grade != null) graded++;
      if (new Date(r.created_at) >= weekAgo) recent7d++;
    }
    return { total: rows.length, graded, recent7d, recent: rows.slice(0, 8) };
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
      const key = r.created_at.slice(0, 7);
      counts[key] = (counts[key] ?? 0) + 1;
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
        <StatCard label="Graded" value={graded} color="#0077b6" />
        <StatCard label="This Week" value={recent7d} color="#0f9b8e" />
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

      {/* Monthly trend */}
      <div className="card">
        <h2>Monthly Volume</h2>
        {monthlyData.length > 0 ? (
          <BarChart data={monthlyData} labelWidth={80} />
        ) : (
          <p style={{ color: "#64748b", fontSize: 14 }}>No session data yet.</p>
        )}
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
