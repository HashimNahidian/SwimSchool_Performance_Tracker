import { FormEvent, useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth";
import type { ManagerEvaluationQuery } from "../api";
import {
  createLevel,
  createSkill,
  createTemplate,
  createUser,
  emailEvaluationsCsv,
  exportEvaluationsCsvUrl,
  listAttributes,
  listLevels,
  listManagerEvaluationsWithQuery,
  listSkills,
  listTemplates,
  listUsers,
  updateTemplate
} from "../api";
import type { Attribute, EvaluationSummary, Level, Skill, TemplateConfig, User, UserRole } from "../types";
import { Section } from "../components/Section";
import { EvaluationTable } from "../components/EvaluationTable";
import { DonutChart } from "../components/DonutChart";

type ManagerTab = "dashboard" | "users" | "levels" | "skills" | "templates" | "evaluations";

const MANAGER_TABS: ManagerTab[] = ["dashboard", "users", "levels", "skills", "templates", "evaluations"];

const SORT_FIELDS = new Set<NonNullable<ManagerEvaluationQuery["sort_by"]>>([
  "id", "session_date", "submitted_at", "instructor_id", "supervisor_id", "level_id", "skill_id"
]);

function parsePositiveInt(value: string): number | undefined {
  if (!value.trim()) return undefined;
  const n = Number.parseInt(value, 10);
  return Number.isNaN(n) ? undefined : n;
}

function buildQuery(filters: Record<string, string>): ManagerEvaluationQuery {
  const q: ManagerEvaluationQuery = {
    limit: parsePositiveInt(filters.limit) ?? 50,
    offset: parsePositiveInt(filters.offset) ?? 0
  };
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
  if (filters.status === "DRAFT" || filters.status === "SUBMITTED") q.status = filters.status;
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
  const [attributes, setAttributes] = useState<Attribute[]>([]);
  const [templates, setTemplates] = useState<TemplateConfig[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationSummary[]>([]);
  const [filters, setFilters] = useState({
    instructor_id: "", supervisor_id: "", level_id: "", skill_id: "",
    rating_value: "", date_from: "", date_to: "", status: "",
    sort_by: "submitted_at", sort_dir: "desc", limit: "50", offset: "0"
  });
  const [appliedQuery, setAppliedQuery] = useState<ManagerEvaluationQuery>({
    sort_by: "submitted_at", sort_dir: "desc", limit: 50, offset: 0
  });

  useEffect(() => {
    if (!token) return;
    Promise.all([
      listUsers(token), listLevels(token), listSkills(token),
      listAttributes(token), listTemplates(token),
      listManagerEvaluationsWithQuery(token, appliedQuery)
    ])
      .then(([u, l, s, a, t, e]) => {
        setUsers(u); setLevels(l); setSkills(s);
        setAttributes(a); setTemplates(t); setEvaluations(e);
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

  if (!token) return null;

  return (
    <>
      {error && <p className="error">{error}</p>}
      <nav className="tabs">
        {MANAGER_TABS.map((item) => (
          <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>
            {item}
          </button>
        ))}
      </nav>

      {tab === "dashboard" && (
        <ManagerDashboard
          rows={evaluations}
          onGo={setTab}
          onConfigureTemplates={() => setTab("templates")}
          onExportCsv={downloadCsv}
          onEmailCsv={sendCsvEmail}
          appliedManagerQuery={appliedQuery}
        />
      )}
      {tab === "users" && (
        <ManagerUsers token={token} users={users} onCreated={(u) => setUsers((p) => [...p, u])} />
      )}
      {tab === "levels" && (
        <ManagerLevels token={token} levels={levels} onCreated={(l) => setLevels((p) => [...p, l])} />
      )}
      {tab === "skills" && (
        <ManagerSkills token={token} levels={levels} skills={skills} onCreated={(s) => setSkills((p) => [...p, s])} />
      )}
      {tab === "templates" && (
        <ManagerTemplates
          token={token} levels={levels} skills={skills} attributes={attributes} templates={templates}
          onCreated={(t) => setTemplates((p) => [...p, t])}
          onUpdated={(t) => setTemplates((p) => p.map((item) => (item.id === t.id ? t : item)))}
        />
      )}
      {tab === "evaluations" && (
        <Section title="All Evaluations">
          <form className="form inline" onSubmit={(e) => { e.preventDefault(); setAppliedQuery(buildQuery(filters)); }}>
            <input placeholder="instructor id" value={filters.instructor_id}
              onChange={(e) => setFilters((p) => ({ ...p, instructor_id: e.target.value, offset: "0" }))} />
            <input placeholder="supervisor id" value={filters.supervisor_id}
              onChange={(e) => setFilters((p) => ({ ...p, supervisor_id: e.target.value, offset: "0" }))} />
            <select value={filters.level_id}
              onChange={(e) => setFilters((p) => ({ ...p, level_id: e.target.value, offset: "0" }))}>
              <option value="">all levels</option>
              {levels.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
            <select value={filters.skill_id}
              onChange={(e) => setFilters((p) => ({ ...p, skill_id: e.target.value, offset: "0" }))}>
              <option value="">all skills</option>
              {skills.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <select value={filters.rating_value}
              onChange={(e) => setFilters((p) => ({ ...p, rating_value: e.target.value, offset: "0" }))}>
              <option value="">all ratings</option>
              <option value="1">1</option><option value="2">2</option><option value="3">3</option>
            </select>
            <select value={filters.status}
              onChange={(e) => setFilters((p) => ({ ...p, status: e.target.value, offset: "0" }))}>
              <option value="">all statuses</option>
              <option value="DRAFT">DRAFT</option><option value="SUBMITTED">SUBMITTED</option>
            </select>
            <input type="date" value={filters.date_from}
              onChange={(e) => setFilters((p) => ({ ...p, date_from: e.target.value, offset: "0" }))} />
            <input type="date" value={filters.date_to}
              onChange={(e) => setFilters((p) => ({ ...p, date_to: e.target.value, offset: "0" }))} />
            <select value={filters.sort_by}
              onChange={(e) => setFilters((p) => ({ ...p, sort_by: e.target.value, offset: "0" }))}>
              <option value="submitted_at">submitted_at</option>
              <option value="session_date">session_date</option>
              <option value="id">id</option>
              <option value="instructor_id">instructor_id</option>
              <option value="supervisor_id">supervisor_id</option>
              <option value="level_id">level_id</option>
              <option value="skill_id">skill_id</option>
            </select>
            <select value={filters.sort_dir}
              onChange={(e) => setFilters((p) => ({ ...p, sort_dir: e.target.value, offset: "0" }))}>
              <option value="desc">desc</option><option value="asc">asc</option>
            </select>
            <input placeholder="limit" value={filters.limit}
              onChange={(e) => setFilters((p) => ({ ...p, limit: e.target.value }))} />
            <input placeholder="offset" value={filters.offset}
              onChange={(e) => setFilters((p) => ({ ...p, offset: e.target.value }))} />
            <button type="submit">Apply Filters</button>
          </form>
          <a href={exportEvaluationsCsvUrl()} target="_blank" rel="noreferrer" className="button-link"
            onClick={(e) => { if (!token) return; e.preventDefault(); downloadCsv(); }}>
            Export CSV
          </a>
          <EvaluationTable rows={evaluations} />
        </Section>
      )}
    </>
  );
}

/* ---- Sub-components ---- */

function ManagerUsers({ token, users, onCreated }: { token: string; users: User[]; onCreated: (u: User) => void }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("INSTRUCTOR");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const user = await createUser(token, { name, email, password, role, active: true });
    onCreated(user);
    setName(""); setEmail(""); setPassword("");
  }

  return (
    <Section title="Users">
      <form className="form inline" onSubmit={onSubmit}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="name" required />
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email" type="email" required />
        <input value={password} onChange={(e) => setPassword(e.target.value)}
          placeholder="password (8+ chars)" minLength={8} type="password" required />
        <select value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
          <option value="MANAGER">MANAGER</option>
          <option value="SUPERVISOR">SUPERVISOR</option>
          <option value="INSTRUCTOR">INSTRUCTOR</option>
        </select>
        <button type="submit">Add user</button>
      </form>
      <table>
        <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Active</th></tr></thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.name}</td><td>{u.email}</td><td>{u.role}</td><td>{u.active ? "yes" : "no"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
  );
}

function ManagerLevels({ token, levels, onCreated }: { token: string; levels: Level[]; onCreated: (l: Level) => void }) {
  const [name, setName] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const level = await createLevel(token, { name, active: true });
    onCreated(level); setName("");
  }

  return (
    <Section title="Levels">
      <form className="form inline" onSubmit={onSubmit}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="level name" required />
        <button type="submit">Add level</button>
      </form>
      <ul style={{ paddingLeft: 20 }}>
        {levels.map((l) => <li key={l.id}>{l.name} ({l.active ? "active" : "inactive"})</li>)}
      </ul>
    </Section>
  );
}

function ManagerSkills({
  token, levels, skills, onCreated
}: { token: string; levels: Level[]; skills: Skill[]; onCreated: (s: Skill) => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [levelId, setLevelId] = useState<number>(levels[0]?.id ?? 0);

  useEffect(() => {
    if (!levelId && levels.length > 0) setLevelId(levels[0].id);
  }, [levelId, levels]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const skill = await createSkill(token, { name, description, level_id: levelId, active: true });
    onCreated(skill); setName(""); setDescription("");
  }

  return (
    <Section title="Skills">
      <form className="form inline" onSubmit={onSubmit}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="skill name" required />
        <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="description" />
        <select value={levelId} onChange={(e) => setLevelId(Number(e.target.value))}>
          {levels.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
        </select>
        <button type="submit">Add skill</button>
      </form>
      <ul style={{ paddingLeft: 20 }}>
        {skills.map((s) => (
          <li key={s.id}>{s.name} (level {s.level_id}){s.description ? ` — ${s.description}` : ""}</li>
        ))}
      </ul>
    </Section>
  );
}

function ManagerTemplates({
  token, levels, skills, attributes, templates, onCreated, onUpdated
}: {
  token: string; levels: Level[]; skills: Skill[]; attributes: Attribute[];
  templates: TemplateConfig[];
  onCreated: (t: TemplateConfig) => void;
  onUpdated: (t: TemplateConfig) => void;
}) {
  const [name, setName] = useState("");
  const [levelId, setLevelId] = useState<number>(levels[0]?.id ?? 0);
  const [skillId, setSkillId] = useState<number>(0);
  const [selected, setSelected] = useState<Record<number, number>>({});
  const [createError, setCreateError] = useState("");
  const levelSkills = useMemo(() => skills.filter((x) => x.level_id === levelId), [skills, levelId]);
  const levelMap = useMemo(() => new Map(levels.map((l) => [l.id, l.name])), [levels]);
  const skillMap = useMemo(() => new Map(skills.map((s) => [s.id, s.name])), [skills]);

  useEffect(() => { if (!levelId && levels.length > 0) setLevelId(levels[0].id); }, [levelId, levels]);
  useEffect(() => { if (levelSkills.length > 0) setSkillId(levelSkills[0].id); }, [levelSkills]);

  function toggleAttribute(id: number, checked: boolean) {
    setSelected((prev) => {
      if (!checked) { const n = { ...prev }; delete n[id]; return n; }
      const max = Object.values(prev).reduce((m, v) => (v > m ? v : m), 0);
      return { ...prev, [id]: max + 1 };
    });
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const attrs = Object.entries(selected)
      .map(([id, order]) => ({ attribute_id: Number(id), sort_order: order }))
      .sort((a, b) => a.sort_order - b.sort_order);
    if (!name.trim()) { setCreateError("Template name is required."); return; }
    if (!levelId || !skillId) { setCreateError("Level and skill are required."); return; }
    if (attrs.length === 0) { setCreateError("Select at least one criterion."); return; }
    setCreateError("");
    const t = await createTemplate(token, { name: name.trim(), level_id: levelId, skill_id: skillId, active: true, attributes: attrs });
    onCreated(t); setName(""); setSelected({});
  }

  return (
    <Section title="Templates">
      <form className="form" onSubmit={onSubmit}>
        <div className="form inline">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="template name" required />
          <select value={levelId} onChange={(e) => setLevelId(Number(e.target.value))}>
            {levels.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
          </select>
          <select value={skillId} onChange={(e) => setSkillId(Number(e.target.value))}>
            {levelSkills.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
        <div className="form">
          {attributes.map((attr) => {
            const checked = selected[attr.id] !== undefined;
            return (
              <label key={attr.id} className="inline-rating">
                <input type="checkbox" checked={checked}
                  onChange={(e) => toggleAttribute(attr.id, e.target.checked)} />
                <span>{attr.name}</span>
                <input type="number" min={1} disabled={!checked}
                  value={checked ? selected[attr.id] : ""}
                  onChange={(e) => setSelected((p) => ({ ...p, [attr.id]: Number.parseInt(e.target.value || "1", 10) }))}
                  style={{ width: 90 }} />
              </label>
            );
          })}
        </div>
        <button type="submit">Create Template</button>
        {createError && <p className="error">{createError}</p>}
      </form>
      <table>
        <thead><tr><th>Name</th><th>Level</th><th>Skill</th><th>Criteria</th><th>Active</th><th>Action</th></tr></thead>
        <tbody>
          {templates.map((t) => (
            <tr key={t.id}>
              <td>{t.name}</td>
              <td>{levelMap.get(t.level_id) ?? "-"}</td>
              <td>{skillMap.get(t.skill_id) ?? "-"}</td>
              <td>{t.attributes.length}</td>
              <td>{t.active ? "yes" : "no"}</td>
              <td>
                <button onClick={async () => { const u = await updateTemplate(token, t.id, { active: !t.active }); onUpdated(u); }}>
                  {t.active ? "Deactivate" : "Activate"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
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

function ManagerDashboard({
  rows, onGo, onConfigureTemplates, onExportCsv, onEmailCsv, appliedManagerQuery
}: {
  rows: EvaluationSummary[];
  onGo: (tab: ManagerTab) => void;
  onConfigureTemplates: () => void;
  onExportCsv: () => void;
  onEmailCsv: (payload: { to: string[]; subject?: string; message?: string; filters?: ManagerEvaluationQuery }) => Promise<void>;
  appliedManagerQuery: ManagerEvaluationQuery;
}) {
  const { total, draft, submitted, recent7d, recent } = useMemo(() => {
    const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    let draft = 0, submitted = 0, recent7d = 0;
    for (const r of rows) {
      if (r.status === "DRAFT") draft++; else submitted++;
      if (r.session_date && new Date(r.session_date) >= weekAgo) recent7d++;
    }
    return { total: rows.length, draft, submitted, recent7d, recent: rows.slice(0, 8) };
  }, [rows]);

  const [showEmail, setShowEmail] = useState(false);
  const [toText, setToText] = useState("");
  const [subject, setSubject] = useState("Propel Swim Evaluations Export");
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
        subject: subject.trim() || "Propel Swim Evaluations Export",
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
        <StatCard label="Total Evaluations" value={total} color="#0a3d62" />
        <StatCard label="Draft / Pending" value={draft} color="#1565c0" />
        <StatCard label="Submitted" value={submitted} color="#0f766e" />
        <StatCard label="Recent 7 Days" value={recent7d} color="#7c3aed" />
      </div>

      {/* Key insight */}
      {draft > 0 && (
        <div className="key-insight">
          <span className="key-insight-icon">💡</span>
          <span className="key-insight-text">
            <strong>{draft}</strong> evaluation{draft !== 1 ? "s" : ""} awaiting submission.
          </span>
        </div>
      )}

      {/* Quick actions */}
      <div className="card" style={{ padding: "16px 24px" }}>
        <div className="dash-actions">
          <button onClick={() => onGo("users")}>Manage Users</button>
          <button onClick={onConfigureTemplates}>Templates</button>
          <button onClick={() => onGo("levels")}>Levels</button>
          <button onClick={() => onGo("skills")}>Skills</button>
          <button onClick={() => onGo("evaluations")}>All Evaluations</button>
          <button onClick={onExportCsv}>Export CSV</button>
          <button onClick={() => setShowEmail((p) => !p)}>
            {showEmail ? "✕ Close Email" : "Email CSV"}
          </button>
        </div>
        {showEmail && (
          <form className="form" onSubmit={onSubmitEmail} style={{ marginTop: 16, marginBottom: 0 }}>
            <label>
              To (comma-separated)
              <input value={toText} onChange={(e) => setToText(e.target.value)} placeholder="someone@example.com" required />
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

      {/* Performance overview + distribution */}
      <div className="two-col">
        <div className="card">
          <h2>Performance Overview</h2>
          <table>
            <thead>
              <tr>
                <th>Instructor</th>
                <th>Supervisor</th>
                <th>Level</th>
                <th>Date</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((row) => (
                <tr key={row.id}>
                  <td>{row.instructor_name}</td>
                  <td>{row.supervisor_name}</td>
                  <td>{row.level_name}</td>
                  <td>{row.session_date}</td>
                  <td>
                    <span className={row.status === "SUBMITTED" ? "badge-submitted" : "badge-draft"}>
                      {row.status}
                    </span>
                  </td>
                </tr>
              ))}
              {recent.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ color: "#64748b" }}>No evaluations yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="card">
          <h2>Distribution</h2>
          <DonutChart submitted={submitted} draft={draft} total={total} />
        </div>
      </div>
    </>
  );
}
