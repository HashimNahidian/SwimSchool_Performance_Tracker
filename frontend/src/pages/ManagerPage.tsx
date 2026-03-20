import { FormEvent, type Dispatch, type SetStateAction, useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth";
import type { ManagerEvaluationQuery } from "../api";
import {
  createAttribute,
  createManagerScheduledEvaluation,
  createLevel,
  createSkill,
  createUser,
  deleteAttribute,
  deleteManagerEvaluation,
  deleteManagerScheduledEvaluation,
  deleteLevel,
  deleteSkill,
  deleteUser,
  emailEvaluationsCsv,
  exportEvaluationsCsvUrl,
  getManagerEvaluationDetail,
  linkSkillAttribute,
  listManagerSkillAttributes,
  listAttributes,
  listLevels,
  listManagerScheduledEvaluations,
  listManagerEvaluationsWithQuery,
  listSkills,
  listUsers,
  unlinkSkillAttribute,
  updateAttribute,
  updateManagerScheduledEvaluation,
  updateLevel,
  updateManagerEvaluation,
  updateSkill,
  updateUser,
} from "../api";
import type { Attribute, EvaluationDetail, EvaluationSummary, Level, ScheduledEvaluation, ScheduledEvaluationStatus, Skill, User, UserRole } from "../types";
import { Section } from "../components/Section";
import { EvaluationTable } from "../components/EvaluationTable";
import { BarChart } from "../components/BarChart";
import { EvaluationReportModal } from "../components/EvaluationReport";
import { EvaluationEditModal } from "../components/EvaluationEditModal";
import { EvaluationFiltersCard, type EvaluationFilterValues } from "../components/EvaluationFiltersCard";
import { EvaluationMonthlyStats } from "../components/EvaluationMonthlyStats";

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

function parseSortOption(sortOption: string): {
  sortBy: NonNullable<ManagerEvaluationQuery["sort_by"]>;
  sortDir: NonNullable<ManagerEvaluationQuery["sort_dir"]>;
} {
  const [sortByRaw, sortDirRaw] = sortOption.split(":");
  const sortBy = SORT_FIELDS.has(sortByRaw as NonNullable<ManagerEvaluationQuery["sort_by"]>)
    ? (sortByRaw as NonNullable<ManagerEvaluationQuery["sort_by"]>)
    : "created_at";
  const sortDir = sortDirRaw === "asc" ? "asc" : "desc";
  return { sortBy, sortDir };
}

function buildQuery(filters: EvaluationFilterValues): ManagerEvaluationQuery {
  const q: ManagerEvaluationQuery = {};
  const instructorId = parsePositiveInt(filters.instructor_id);
  const supervisorId = parsePositiveInt(filters.supervisor_id);
  const skillId = parsePositiveInt(filters.skill_id);
  const finalGrade = parsePositiveInt(filters.final_grade);
  if (instructorId !== undefined) q.instructor_id = instructorId;
  if (supervisorId !== undefined) q.supervisor_id = supervisorId;
  if (skillId !== undefined) q.skill_id = skillId;
  if (finalGrade !== undefined) q.final_grade = finalGrade;
  if (filters.needs_reevaluation) q.needs_reevaluation = filters.needs_reevaluation === "true";
  if (filters.date_from) q.date_from = filters.date_from;
  if (filters.date_to) q.date_to = filters.date_to;
  const { sortBy, sortDir } = parseSortOption(filters.sort_option);
  q.sort_by = sortBy;
  q.sort_dir = sortDir;
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
  const [scheduledEvaluations, setScheduledEvaluations] = useState<ScheduledEvaluation[]>([]);
  const [reportEval, setReportEval] = useState<EvaluationDetail | null>(null);
  const [editEval, setEditEval] = useState<EvaluationDetail | null>(null);
  const [pendingDeleteEval, setPendingDeleteEval] = useState<EvaluationSummary | null>(null);
  const [loadingReport, setLoadingReport] = useState(false);
  const [filters, setFilters] = useState<EvaluationFilterValues>({
    instructor_id: "", supervisor_id: "", skill_id: "",
    final_grade: "", needs_reevaluation: "", date_from: "", date_to: "",
    sort_option: "created_at:desc", selected_days: []
  });
  const [appliedQuery, setAppliedQuery] = useState<ManagerEvaluationQuery>({
    sort_by: "created_at", sort_dir: "desc", limit: EVALUATIONS_PAGE_SIZE, offset: 0
  });
  const [evaluationsPage, setEvaluationsPage] = useState(0);
  const [appliedSelectedDays, setAppliedSelectedDays] = useState<number[]>([]);
  const [scheduleForm, setScheduleForm] = useState({
    instructorId: "",
    supervisorId: "",
    levelId: "",
    skillId: "",
    targetDate: new Date().toISOString().slice(0, 10),
    notes: "",
  });
  const [editingScheduleId, setEditingScheduleId] = useState<number | null>(null);
  const visibleEvaluations = useMemo(() => {
    if (appliedSelectedDays.length === 0) return evaluations;
    return evaluations.filter((row) => appliedSelectedDays.includes(new Date(row.created_at).getDay()));
  }, [appliedSelectedDays, evaluations]);
  const unreadEvaluationsCount = useMemo(
    () => evaluations.filter((row) => !row.instructor_acknowledged_at).length,
    [evaluations]
  );

  useEffect(() => {
    if (!token) return;
    Promise.all([
      listUsers(token), listLevels(token), listSkills(token), listAttributes(token),
      listManagerEvaluationsWithQuery(token, appliedQuery),
      listManagerScheduledEvaluations(token),
    ])
      .then(([u, l, s, a, e, scheduled]) => {
        setUsers(u);
        setLevels(l);
        setSkills(s);
        setAttributes(a);
        setEvaluations(e);
        setScheduledEvaluations(scheduled);
      })
      .catch((e: Error) => setError(e.message));
  }, [token, appliedQuery]);

  const scheduleSkills = useMemo(
    () => skills.filter((skill) => !scheduleForm.levelId || skill.level_id === Number(scheduleForm.levelId)),
    [scheduleForm.levelId, skills]
  );

  async function refreshScheduledEvaluations() {
    if (!token) return;
    const scheduled = await listManagerScheduledEvaluations(token);
    setScheduledEvaluations(scheduled);
  }

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

  function handleDeleteEval(id: number) {
    const target = evaluations.find((item) => item.id === id);
    if (!target) return;
    setPendingDeleteEval(target);
  }

  async function confirmDeleteEval() {
    if (!token) return;
    const target = pendingDeleteEval;
    if (!target) return;
    try {
      setError("");
      await deleteManagerEvaluation(token, target.id);
      setEvaluations((prev) => prev.filter((item) => item.id !== target.id));
      if (reportEval?.id === target.id) setReportEval(null);
      if (editEval?.id === target.id) setEditEval(null);
      setPendingDeleteEval(null);
    } catch (e) {
      setError((e as Error).message);
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
          onDelete={handleDeleteEval}
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
        <>
          <div className="page-heading">
            <h1 className="page-title">Evaluation History</h1>
            <p className="page-subtitle">Review, filter, export, and manage evaluations across the whole program.</p>
          </div>

          <EvaluationMonthlyStats rows={visibleEvaluations} flaggedLabel="Evaluations needing reevaluation" />
          <div className="card" style={{ marginBottom: 20 }}>
            <h2 style={{ marginBottom: 8 }}>Read Status</h2>
            <p style={{ margin: 0, fontSize: 16, fontWeight: 700, color: "#023e8a" }}>
              Unread evaluations: {unreadEvaluationsCount}
            </p>
          </div>

          <div className="evaluation-layout">
            <aside className="evaluation-sidebar">
              <EvaluationFiltersCard
                title="Filter Evaluations"
                filters={filters}
                setFilters={setFilters}
                skills={skills}
                instructors={users.filter((u) => u.role === "INSTRUCTOR")}
                supervisors={users.filter((u) => u.role === "SUPERVISOR")}
                showSupervisorFilter
                onApply={() => {
                  setEvaluationsPage(0);
                  setAppliedSelectedDays(filters.selected_days);
                  setAppliedQuery({ ...buildQuery(filters), limit: EVALUATIONS_PAGE_SIZE, offset: 0 });
                }}
                onClear={() => {
                  const nextFilters: EvaluationFilterValues = {
                    instructor_id: "",
                    supervisor_id: "",
                    skill_id: "",
                    final_grade: "",
                    needs_reevaluation: "",
                    date_from: "",
                    date_to: "",
                    sort_option: "created_at:desc",
                    selected_days: [],
                  };
                  setFilters(nextFilters);
                  setEvaluationsPage(0);
                  setAppliedSelectedDays([]);
                  setAppliedQuery({ sort_by: "created_at", sort_dir: "desc", limit: EVALUATIONS_PAGE_SIZE, offset: 0 });
                }}
                actions={(
                  <a
                    href={exportEvaluationsCsvUrl()}
                    target="_blank"
                    rel="noreferrer"
                    className="button-link"
                    onClick={(e) => { if (!token) return; e.preventDefault(); downloadCsv(); }}
                  >
                    Export CSV
                  </a>
                )}
              />
            </aside>

            <div className="evaluation-main">
              {/* moved assigned evaluation panel from Dashboard to Evaluations page for manager */}
              <ManagerScheduledEvaluations
                token={token}
                users={users}
                levels={levels}
                schedules={scheduledEvaluations}
                form={scheduleForm}
                editingScheduleId={editingScheduleId}
                scheduleSkills={scheduleSkills}
                onFormChange={setScheduleForm}
                onStartEdit={setEditingScheduleId}
                onRefresh={refreshScheduledEvaluations}
                onSetError={setError}
              />
              <Section title={`All Evaluations${loadingReport ? " — Loading report…" : ""}`}>
          <EvaluationTable
            rows={visibleEvaluations}
            onView={handleViewReport}
            onEdit={handleEditEval}
            onDelete={handleDeleteEval}
            showAcknowledged
          />
          {visibleEvaluations.length === 0 && (
            <p style={{ color: "#64748b", fontSize: 14, paddingTop: 8 }}>No evaluations match the current filters.</p>
          )}
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
            </div>
          </div>
        </>
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
            setEvaluations((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
            setEditEval(null);
          }}
          onSubmitted={() => setEditEval(null)}
          onClose={() => setEditEval(null)}
        />
      )}

      {pendingDeleteEval && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
            zIndex: 1000,
          }}
        >
          <div
            style={{
              width: "min(420px, 100%)",
              background: "white",
              borderRadius: 16,
              padding: 24,
              boxShadow: "0 24px 60px rgba(15, 23, 42, 0.22)",
            }}
          >
            <h3 style={{ marginTop: 0, marginBottom: 12 }}>Delete Evaluation</h3>
            <p style={{ marginTop: 0, marginBottom: 20 }}>
              Are you sure you want to delete this eval?
            </p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button type="button" className="btn-add" onClick={() => setPendingDeleteEval(null)}>
                No
              </button>
              <button
                type="button"
                onClick={() => { void confirmDeleteEval(); }}
                style={{ background: "#c2410c" }}
              >
                Yes
              </button>
            </div>
          </div>
        </div>
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
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("INSTRUCTOR");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editFullName, setEditFullName] = useState("");
  const [editUsername, setEditUsername] = useState("");
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
        username,
        email: email.trim() || null,
        phone: phone.trim() || null,
        password,
        role,
        is_active: true,
      });
      onCreated(user);
      setFullName("");
      setUsername("");
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
    setEditUsername(user.username);
    setEditEmail(user.email ?? "");
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
        username: string;
        email: string | null;
        phone: string | null;
        role: UserRole;
        is_active: boolean;
        password?: string;
      } = {
        full_name: editFullName,
        username: editUsername,
        email: editEmail.trim() || null,
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
        <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" required />
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email (optional)" type="email" />
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
              <thead><tr><th>Name</th><th>Username</th><th>Email</th><th>Phone</th><th>Role</th><th>Active</th><th>Actions</th></tr></thead>
              <tbody>
                {list.map((u) => (
                  <tr key={u.id}>
                    {editingId === u.id ? (
                      <>
                        <td><input value={editFullName} onChange={(e) => setEditFullName(e.target.value)} /></td>
                        <td><input value={editUsername} onChange={(e) => setEditUsername(e.target.value)} /></td>
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
                        <td>{u.username}</td>
                        <td>{u.email ?? "-"}</td>
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

type LevelsSubTab = "levels" | "skills";

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
  const [activeSkillAttributesId, setActiveSkillAttributesId] = useState<number | null>(null);
  const [linkedAttributes, setLinkedAttributes] = useState<Attribute[]>([]);
  const [existingAttributeId, setExistingAttributeId] = useState<number>(0);

  // ── Attributes state ──
  const [attrName, setAttrName] = useState("");
  const [attrDesc, setAttrDesc] = useState("");
  const [editingAttrId, setEditingAttrId] = useState<number | null>(null);
  const [editAttrName, setEditAttrName] = useState("");
  const [editAttrDesc, setEditAttrDesc] = useState("");
  const activeSkill = useMemo(
    () => skills.find((skill) => skill.id === activeSkillAttributesId) ?? null,
    [skills, activeSkillAttributesId]
  );
  const availableAttributes = useMemo(
    () => attributes.filter((attribute) => !linkedAttributes.some((linked) => linked.id === attribute.id)),
    [attributes, linkedAttributes]
  );

  const [error, setError] = useState("");

  useEffect(() => {
    if (!skillLevelId && levels.length > 0) setSkillLevelId(levels[0].id);
  }, [skillLevelId, levels]);

  useEffect(() => {
    if (activeSkillAttributesId == null) {
      setLinkedAttributes([]);
      setExistingAttributeId(0);
      return;
    }
    listManagerSkillAttributes(token, activeSkillAttributesId)
      .then((items) => {
        setLinkedAttributes(items);
        setExistingAttributeId((current) => (current && items.some((item) => item.id === current) ? current : 0));
      })
      .catch((err: Error) => setError(err.message));
  }, [activeSkillAttributesId, token]);

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
  async function attachExistingAttribute() {
    if (!activeSkillAttributesId || !existingAttributeId) return;
    try {
      setError("");
      await linkSkillAttribute(token, activeSkillAttributesId, existingAttributeId);
      const attribute = attributes.find((item) => item.id === existingAttributeId);
      if (attribute) {
        setLinkedAttributes((prev) => [...prev, attribute]);
      }
      setExistingAttributeId(0);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function onCreateAttribute(e: FormEvent) {
    e.preventDefault();
    if (!activeSkillAttributesId) return;
    try {
      setError("");
      const attr = await createAttribute(token, { name: attrName, description: attrDesc.trim() || null });
      await linkSkillAttribute(token, activeSkillAttributesId, attr.id);
      onAttributeCreated(attr);
      setLinkedAttributes((prev) => [...prev, attr]);
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
      setLinkedAttributes((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
      setEditingAttrId(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function detachAttribute(attributeId: number) {
    if (!activeSkillAttributesId) return;
    try {
      setError("");
      await unlinkSkillAttribute(token, activeSkillAttributesId, attributeId);
      setLinkedAttributes((prev) => prev.filter((item) => item.id !== attributeId));
      if (editingAttrId === attributeId) setEditingAttrId(null);
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
      setLinkedAttributes((prev) => prev.filter((item) => item.id !== attr.id));
      if (editingAttrId === attr.id) setEditingAttrId(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <Section title="Curriculum">
      <nav className="tabs" style={{ marginBottom: 16 }}>
        {(["levels", "skills"] as LevelsSubTab[]).map((t) => (
          <button key={t} className={subTab === t ? "active" : ""} onClick={() => { setSubTab(t); setError(""); }}>
            {t === "levels" ? "Levels" : "Skills"}
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
                          <button
                            type="button"
                            onClick={() => {
                              setActiveSkillAttributesId((current) => (current === s.id ? null : s.id));
                              setEditingAttrId(null);
                              setAttrName("");
                              setAttrDesc("");
                              setError("");
                            }}
                          >
                            Attributes
                          </button>
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

      {subTab === "skills" && activeSkill && (
        <div style={{ marginTop: 18, padding: 18, border: "1px solid #d7e4ef", borderRadius: 14, background: "#f8fbfe" }}>
          <h3 style={{ marginTop: 0, marginBottom: 8 }}>Attributes For {activeSkill.name}</h3>
          <p style={{ marginTop: 0, marginBottom: 16, color: "#64748b", fontSize: 14 }}>
            These are the attributes that will appear when a supervisor evaluates this skill.
          </p>

          <div style={{ display: "grid", gap: 12, marginBottom: 18 }}>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
              <select
                value={existingAttributeId}
                onChange={(e) => setExistingAttributeId(Number(e.target.value))}
                style={{ minWidth: 240 }}
              >
                <option value={0}>Link existing attribute</option>
                {availableAttributes.map((attribute) => (
                  <option key={attribute.id} value={attribute.id}>
                    {attribute.name}
                  </option>
                ))}
              </select>
              <button type="button" onClick={() => { void attachExistingAttribute(); }} disabled={existingAttributeId === 0}>
                Add Existing Attribute
              </button>
            </div>

            <form className="form inline" onSubmit={onCreateAttribute}>
              <input value={attrName} onChange={(e) => setAttrName(e.target.value)} placeholder="New attribute name" required />
              <input value={attrDesc} onChange={(e) => setAttrDesc(e.target.value)} placeholder="Description (optional)" />
              <button type="submit">Create And Add</button>
            </form>
          </div>

          <table>
            <thead><tr><th>Name</th><th>Description</th><th>Actions</th></tr></thead>
            <tbody>
              {linkedAttributes.map((attribute) => (
                <tr key={attribute.id}>
                  {editingAttrId === attribute.id ? (
                    <>
                      <td><input value={editAttrName} onChange={(e) => setEditAttrName(e.target.value)} /></td>
                      <td><input value={editAttrDesc} onChange={(e) => setEditAttrDesc(e.target.value)} placeholder="Description (optional)" /></td>
                      <td>
                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                          <button type="button" onClick={() => saveAttribute(attribute.id)}>Save</button>
                          <button type="button" className="btn-add" onClick={() => setEditingAttrId(null)}>Cancel</button>
                        </div>
                      </td>
                    </>
                  ) : (
                    <>
                      <td>{attribute.name}</td>
                      <td style={{ color: "#64748b", fontSize: 13 }}>{attribute.description ?? "—"}</td>
                      <td>
                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                          <button
                            type="button"
                            onClick={() => {
                              setEditingAttrId(attribute.id);
                              setEditAttrName(attribute.name);
                              setEditAttrDesc(attribute.description ?? "");
                              setError("");
                            }}
                          >
                            Edit
                          </button>
                          <button type="button" onClick={() => { void detachAttribute(attribute.id); }}>
                            Remove From Skill
                          </button>
                          <button type="button" className="btn-add" onClick={() => removeAttribute(attribute)}>
                            Delete
                          </button>
                        </div>
                      </td>
                    </>
                  )}
                </tr>
              ))}
              {linkedAttributes.length === 0 && (
                <tr>
                  <td colSpan={3} style={{ color: "#64748b" }}>
                    No attributes linked yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
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

function ManagerScheduledEvaluations({
  token,
  users,
  levels,
  schedules,
  form,
  editingScheduleId,
  scheduleSkills,
  onFormChange,
  onStartEdit,
  onRefresh,
  onSetError,
}: {
  token: string;
  users: User[];
  levels: Level[];
  schedules: ScheduledEvaluation[];
  form: {
    instructorId: string;
    supervisorId: string;
    levelId: string;
    skillId: string;
    targetDate: string;
    notes: string;
  };
  editingScheduleId: number | null;
  scheduleSkills: Skill[];
  onFormChange: Dispatch<SetStateAction<{
    instructorId: string;
    supervisorId: string;
    levelId: string;
    skillId: string;
    targetDate: string;
    notes: string;
  }>>;
  onStartEdit: Dispatch<SetStateAction<number | null>>;
  onRefresh: () => Promise<void>;
  onSetError: Dispatch<SetStateAction<string>>;
}) {
  const supervisors = users.filter((user) => user.role === "SUPERVISOR");
  const instructors = users.filter((user) => user.role === "INSTRUCTOR");
  const activeSchedules = schedules.filter((item) => item.status !== "COMPLETED" && item.status !== "CANCELED");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!form.instructorId || !form.skillId || !form.targetDate) return;
    try {
      const payload = {
        instructor_id: Number(form.instructorId),
        skill_id: Number(form.skillId),
        assigned_to_id: form.supervisorId ? Number(form.supervisorId) : null,
        target_date: form.targetDate,
        notes: form.notes.trim() || null,
      };
      if (editingScheduleId) {
        await updateManagerScheduledEvaluation(token, editingScheduleId, payload);
      } else {
        await createManagerScheduledEvaluation(token, payload);
      }
      onStartEdit(null);
      onFormChange({
        instructorId: "",
        supervisorId: "",
        levelId: "",
        skillId: "",
        targetDate: new Date().toISOString().slice(0, 10),
        notes: "",
      });
      await onRefresh();
    } catch (err) {
      onSetError((err as Error).message);
    }
  }

  async function updateStatus(schedule: ScheduledEvaluation, status: ScheduledEvaluationStatus) {
    try {
      await updateManagerScheduledEvaluation(token, schedule.id, { status });
      await onRefresh();
    } catch (err) {
      onSetError((err as Error).message);
    }
  }

  async function removeSchedule(id: number) {
    try {
      await deleteManagerScheduledEvaluation(token, id);
      await onRefresh();
    } catch (err) {
      onSetError((err as Error).message);
    }
  }

  return (
    <div className="card">
      <h2>Assigned Evaluations</h2>
      <form className="form" onSubmit={handleSubmit}>
        <label>
          Instructor
          <select value={form.instructorId} onChange={(e) => onFormChange((prev) => ({ ...prev, instructorId: e.target.value }))}>
            <option value="">Select instructor</option>
            {instructors.map((user) => (
              <option key={user.id} value={user.id}>{user.full_name}</option>
            ))}
          </select>
        </label>
        <label>
          Assign To
          <select value={form.supervisorId} onChange={(e) => onFormChange((prev) => ({ ...prev, supervisorId: e.target.value }))}>
            <option value="">Unassigned</option>
            {supervisors.map((user) => (
              <option key={user.id} value={user.id}>{user.full_name}</option>
            ))}
          </select>
        </label>
        <label>
          Level
          <select value={form.levelId} onChange={(e) => onFormChange((prev) => ({ ...prev, levelId: e.target.value, skillId: "" }))}>
            <option value="">Select level</option>
            {levels.map((level) => (
              <option key={level.id} value={level.id}>{level.name}</option>
            ))}
          </select>
        </label>
        <label>
          Skill
          <select value={form.skillId} onChange={(e) => onFormChange((prev) => ({ ...prev, skillId: e.target.value }))}>
            <option value="">Select skill</option>
            {scheduleSkills.map((skill) => (
              <option key={skill.id} value={skill.id}>{skill.name}</option>
            ))}
          </select>
        </label>
        <label>
          Target Date
          <input type="date" value={form.targetDate} onChange={(e) => onFormChange((prev) => ({ ...prev, targetDate: e.target.value }))} />
        </label>
        <label>
          Notes
          <textarea value={form.notes} onChange={(e) => onFormChange((prev) => ({ ...prev, notes: e.target.value }))} />
        </label>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button type="submit">{editingScheduleId ? "Update Assignment" : "Schedule Evaluation"}</button>
          {editingScheduleId && (
            <button
              type="button"
              className="btn-add"
              onClick={() => {
                onStartEdit(null);
                onFormChange({
                  instructorId: "",
                  supervisorId: "",
                  levelId: "",
                  skillId: "",
                  targetDate: new Date().toISOString().slice(0, 10),
                  notes: "",
                });
              }}
            >
              Cancel Edit
            </button>
          )}
        </div>
      </form>

      {activeSchedules.length > 0 ? (
        <table style={{ marginTop: 16 }}>
          <thead>
            <tr>
              <th>Instructor</th>
              <th>Level</th>
              <th>Skill</th>
              <th>Target Date</th>
              <th>Assigned To</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {activeSchedules.map((schedule) => (
              <tr key={schedule.id}>
                <td>{schedule.instructor_name}</td>
                <td>{schedule.level_name}</td>
                <td>{schedule.skill_name}</td>
                <td>{new Date(schedule.target_date + "T00:00:00").toLocaleDateString()}</td>
                <td>{schedule.assigned_to_name ?? "Unassigned"}</td>
                <td>{schedule.status}</td>
                <td>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <button type="button" onClick={() => void updateStatus(schedule, "IN_PROGRESS")}>Start</button>
                    <button type="button" className="btn-add" onClick={() => {
                      onStartEdit(schedule.id);
                      onFormChange({
                        instructorId: String(schedule.instructor_id),
                        supervisorId: schedule.assigned_to_id ? String(schedule.assigned_to_id) : "",
                        levelId: String(schedule.level_id),
                        skillId: String(schedule.skill_id),
                        targetDate: schedule.target_date,
                        notes: schedule.notes ?? "",
                      });
                    }}>Edit</button>
                    <button type="button" className="btn-add" onClick={() => void updateStatus(schedule, "CANCELED")}>Cancel</button>
                    <button type="button" className="btn-add" onClick={() => void removeSchedule(schedule.id)}>Delete</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p style={{ color: "#64748b", fontSize: 14 }}>No active scheduled evaluations.</p>
      )}
    </div>
  );
}

function ManagerDashboard({
  rows, onGo, onExportCsv, onEmailCsv, appliedManagerQuery, onView, onEdit, onDelete
}: {
  rows: EvaluationSummary[];
  onGo: (tab: ManagerTab) => void;
  onExportCsv: () => void;
  onEmailCsv: (payload: { to: string[]; subject?: string; message?: string; filters?: ManagerEvaluationQuery }) => Promise<void>;
  appliedManagerQuery: ManagerEvaluationQuery;
  onView?: (id: number) => void;
  onEdit?: (id: number) => void;
  onDelete?: (id: number) => void;
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

      </div>

      {/* Recent evaluations */}
      <div className="card">
        <h2>Recent Evaluations</h2>
        {recent.length > 0 ? (
          <EvaluationTable rows={recent} onView={onView} onEdit={onEdit} onDelete={onDelete} showAcknowledged />
        ) : (
          <p style={{ color: "#64748b", fontSize: 14 }}>No evaluations yet.</p>
        )}
      </div>
    </>
  );
}
