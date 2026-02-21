import { FormEvent, ReactNode, useMemo, useEffect, useState } from "react";

import {
  createLevel,
  createSkill,
  createSupervisorEvaluation,
  createUser,
  exportEvaluationsCsvUrl,
  listInstructorEvaluations,
  listLevels,
  listManagerEvaluationsWithQuery,
  listSkills,
  listSupervisorEvaluations,
  listUsers,
  login,
  logout,
  me,
  resolveSupervisorTemplate,
  refresh
} from "./api";
import type { ManagerEvaluationQuery } from "./api";
import type { EvaluationSummary, Level, Skill, TemplateResolved, User, UserRole } from "./types";

type AppTab = "dashboard" | "users" | "levels" | "skills" | "evaluations";

function Section({
  title,
  children
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="card">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

const MANAGER_SORT_FIELDS = new Set<NonNullable<ManagerEvaluationQuery["sort_by"]>>([
  "id",
  "session_date",
  "submitted_at",
  "instructor_id",
  "supervisor_id",
  "level_id",
  "skill_id"
]);

function parsePositiveInt(value: string): number | undefined {
  if (!value.trim()) return undefined;
  const n = Number.parseInt(value, 10);
  return Number.isNaN(n) ? undefined : n;
}

function buildManagerQueryFromFilters(filters: {
  instructor_id: string;
  supervisor_id: string;
  level_id: string;
  skill_id: string;
  rating_value: string;
  date_from: string;
  date_to: string;
  status: string;
  sort_by: string;
  sort_dir: string;
  limit: string;
  offset: string;
}): ManagerEvaluationQuery {
  const query: ManagerEvaluationQuery = {
    limit: parsePositiveInt(filters.limit) ?? 50,
    offset: parsePositiveInt(filters.offset) ?? 0
  };
  const instructorId = parsePositiveInt(filters.instructor_id);
  const supervisorId = parsePositiveInt(filters.supervisor_id);
  const levelId = parsePositiveInt(filters.level_id);
  const skillId = parsePositiveInt(filters.skill_id);
  const ratingValue = parsePositiveInt(filters.rating_value);
  if (instructorId !== undefined) query.instructor_id = instructorId;
  if (supervisorId !== undefined) query.supervisor_id = supervisorId;
  if (levelId !== undefined) query.level_id = levelId;
  if (skillId !== undefined) query.skill_id = skillId;
  if (ratingValue !== undefined) query.rating_value = ratingValue;
  if (filters.date_from) query.date_from = filters.date_from;
  if (filters.date_to) query.date_to = filters.date_to;
  if (filters.status === "DRAFT" || filters.status === "SUBMITTED") query.status = filters.status;
  if (MANAGER_SORT_FIELDS.has(filters.sort_by as NonNullable<ManagerEvaluationQuery["sort_by"]>)) {
    query.sort_by = filters.sort_by as NonNullable<ManagerEvaluationQuery["sort_by"]>;
  } else {
    query.sort_by = "submitted_at";
  }
  query.sort_dir = filters.sort_dir === "asc" ? "asc" : "desc";
  return query;
}

export default function App() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState<string | null>(localStorage.getItem("token"));
  const [refreshToken, setRefreshToken] = useState<string | null>(
    localStorage.getItem("refresh_token")
  );
  const [meUser, setMeUser] = useState<User | null>(null);
  const [error, setError] = useState<string>("");
  const [tab, setTab] = useState<AppTab>("dashboard");

  const [users, setUsers] = useState<User[]>([]);
  const [levels, setLevels] = useState<Level[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationSummary[]>([]);
  const [managerFilters, setManagerFilters] = useState({
    instructor_id: "",
    supervisor_id: "",
    level_id: "",
    skill_id: "",
    rating_value: "",
    date_from: "",
    date_to: "",
    status: "",
    sort_by: "submitted_at",
    sort_dir: "desc",
    limit: "50",
    offset: "0"
  });
  const [appliedManagerQuery, setAppliedManagerQuery] = useState<ManagerEvaluationQuery>({
    sort_by: "submitted_at",
    sort_dir: "desc",
    limit: 50,
    offset: 0
  });

  const role = meUser?.role;

  const authHeader = useMemo(
    () => (token ? ({ Authorization: `Bearer ${token}` } as HeadersInit) : undefined),
    [token]
  );

  useEffect(() => {
    if (!token) {
      setMeUser(null);
      return;
    }
    me(token)
      .then(setMeUser)
      .catch(async () => {
        if (!refreshToken) {
          localStorage.removeItem("token");
          localStorage.removeItem("refresh_token");
          setToken(null);
          setRefreshToken(null);
          return;
        }
        try {
          const next = await refresh(refreshToken);
          localStorage.setItem("token", next.access_token);
          localStorage.setItem("refresh_token", next.refresh_token);
          setToken(next.access_token);
          setRefreshToken(next.refresh_token);
        } catch (e) {
          setError((e as Error).message);
          localStorage.removeItem("token");
          localStorage.removeItem("refresh_token");
          setToken(null);
          setRefreshToken(null);
        }
      });
  }, [token, refreshToken]);

  useEffect(() => {
    if (!token || !role) return;
    if (role === "MANAGER") {
      Promise.all([
        listUsers(token),
        listLevels(token),
        listSkills(token),
        listManagerEvaluationsWithQuery(token, appliedManagerQuery)
      ])
        .then(([nextUsers, nextLevels, nextSkills, nextEvaluations]) => {
          setUsers(nextUsers);
          setLevels(nextLevels);
          setSkills(nextSkills);
          setEvaluations(nextEvaluations);
        })
        .catch((e: Error) => setError(e.message));
    } else if (role === "SUPERVISOR") {
      Promise.all([listUsers(token), listLevels(token), listSkills(token), listSupervisorEvaluations(token)])
        .then(([nextUsers, nextLevels, nextSkills, nextEvaluations]) => {
          setUsers(nextUsers.filter((x) => x.role === "INSTRUCTOR"));
          setLevels(nextLevels);
          setSkills(nextSkills);
          setEvaluations(nextEvaluations);
        })
        .catch((e: Error) => setError(e.message));
    } else {
      listInstructorEvaluations(token)
        .then(setEvaluations)
        .catch((e: Error) => setError(e.message));
    }
  }, [role, token, appliedManagerQuery]);

  function downloadCsv() {
    if (!token) return;
    fetch(exportEvaluationsCsvUrl(), { headers: authHeader }).then(async (resp) => {
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "evaluations.csv";
      link.click();
      URL.revokeObjectURL(url);
    });
  }

  function onLogout() {
    if (refreshToken) {
      logout(refreshToken).catch(() => undefined);
    }
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
    setToken(null);
    setRefreshToken(null);
    setMeUser(null);
  }

  async function onLoginSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      const response = await login(email, password);
      localStorage.setItem("token", response.access_token);
      localStorage.setItem("refresh_token", response.refresh_token);
      setToken(response.access_token);
      setRefreshToken(response.refresh_token);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (!token || !meUser) {
    return (
      <main className="layout auth">
        <Section title="Propel Swim Academy Login">
          <form onSubmit={onLoginSubmit} className="form">
            <label>
              Email
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                type="email"
                required
              />
            </label>
            <label>
              Password
              <input
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                type="password"
                required
              />
            </label>
            <button type="submit">Log in</button>
          </form>
          {error ? <p className="error">{error}</p> : null}
        </Section>
      </main>
    );
  }

  return (
    <main className="layout">
      <header className="header">
        <div>
          <h1>Propel Swim Academy Evaluation System</h1>
          <p>
            Signed in as {meUser.name} ({meUser.role})
          </p>
        </div>
        <button onClick={onLogout}>Log out</button>
      </header>

      {error ? <p className="error">{error}</p> : null}

      {role === "MANAGER" ? (
        <>
          <nav className="tabs">
            {(["dashboard", "users", "levels", "skills", "evaluations"] as AppTab[]).map(
              (item) => (
                <button
                  key={item}
                  className={tab === item ? "active" : ""}
                  onClick={() => setTab(item)}
                >
                  {item}
                </button>
              )
            )}
          </nav>
          {tab === "dashboard" ? (
            <ManagerDashboard
              rows={evaluations}
              onGo={setTab}
              onConfigureTemplates={() => setError("Template configuration page coming next.")}
              onExport={downloadCsv}
            />
          ) : null}
          {tab === "users" ? (
            <ManagerUsers
              token={token}
              users={users}
              onCreated={(user) => setUsers((prev) => [...prev, user])}
            />
          ) : null}
          {tab === "levels" ? (
            <ManagerLevels
              token={token}
              levels={levels}
              onCreated={(level) => setLevels((prev) => [...prev, level])}
            />
          ) : null}
          {tab === "skills" ? (
            <ManagerSkills
              token={token}
              levels={levels}
              skills={skills}
              onCreated={(skill) => setSkills((prev) => [...prev, skill])}
            />
          ) : null}
          {tab === "evaluations" ? (
            <Section title="All Evaluations">
              <form
                className="form inline"
                onSubmit={(e) => {
                  e.preventDefault();
                  setAppliedManagerQuery(buildManagerQueryFromFilters(managerFilters));
                }}
              >
                <input
                  placeholder="instructor id"
                  value={managerFilters.instructor_id}
                  onChange={(e) =>
                    setManagerFilters((prev) => ({ ...prev, instructor_id: e.target.value, offset: "0" }))
                  }
                />
                <input
                  placeholder="supervisor id"
                  value={managerFilters.supervisor_id}
                  onChange={(e) =>
                    setManagerFilters((prev) => ({ ...prev, supervisor_id: e.target.value, offset: "0" }))
                  }
                />
                <select
                  value={managerFilters.level_id}
                  onChange={(e) =>
                    setManagerFilters((prev) => ({ ...prev, level_id: e.target.value, offset: "0" }))
                  }
                >
                  <option value="">all levels</option>
                  {levels.map((level) => (
                    <option key={level.id} value={level.id}>
                      {level.name}
                    </option>
                  ))}
                </select>
                <select
                  value={managerFilters.skill_id}
                  onChange={(e) =>
                    setManagerFilters((prev) => ({ ...prev, skill_id: e.target.value, offset: "0" }))
                  }
                >
                  <option value="">all skills</option>
                  {skills.map((skill) => (
                    <option key={skill.id} value={skill.id}>
                      {skill.name}
                    </option>
                  ))}
                </select>
                <select
                  value={managerFilters.rating_value}
                  onChange={(e) =>
                    setManagerFilters((prev) => ({ ...prev, rating_value: e.target.value, offset: "0" }))
                  }
                >
                  <option value="">all ratings</option>
                  <option value="1">1</option>
                  <option value="2">2</option>
                  <option value="3">3</option>
                </select>
                <select
                  value={managerFilters.status}
                  onChange={(e) =>
                    setManagerFilters((prev) => ({ ...prev, status: e.target.value, offset: "0" }))
                  }
                >
                  <option value="">all statuses</option>
                  <option value="DRAFT">DRAFT</option>
                  <option value="SUBMITTED">SUBMITTED</option>
                </select>
                <input
                  type="date"
                  value={managerFilters.date_from}
                  onChange={(e) =>
                    setManagerFilters((prev) => ({ ...prev, date_from: e.target.value, offset: "0" }))
                  }
                />
                <input
                  type="date"
                  value={managerFilters.date_to}
                  onChange={(e) =>
                    setManagerFilters((prev) => ({ ...prev, date_to: e.target.value, offset: "0" }))
                  }
                />
                <select
                  value={managerFilters.sort_by}
                  onChange={(e) =>
                    setManagerFilters((prev) => ({ ...prev, sort_by: e.target.value, offset: "0" }))
                  }
                >
                  <option value="submitted_at">submitted_at</option>
                  <option value="session_date">session_date</option>
                  <option value="id">id</option>
                  <option value="instructor_id">instructor_id</option>
                  <option value="supervisor_id">supervisor_id</option>
                  <option value="level_id">level_id</option>
                  <option value="skill_id">skill_id</option>
                </select>
                <select
                  value={managerFilters.sort_dir}
                  onChange={(e) =>
                    setManagerFilters((prev) => ({ ...prev, sort_dir: e.target.value, offset: "0" }))
                  }
                >
                  <option value="desc">desc</option>
                  <option value="asc">asc</option>
                </select>
                <input
                  placeholder="limit"
                  value={managerFilters.limit}
                  onChange={(e) => setManagerFilters((prev) => ({ ...prev, limit: e.target.value }))}
                />
                <input
                  placeholder="offset"
                  value={managerFilters.offset}
                  onChange={(e) => setManagerFilters((prev) => ({ ...prev, offset: e.target.value }))}
                />
                <button type="submit">Apply Filters</button>
              </form>
              <a
                href={exportEvaluationsCsvUrl()}
                target="_blank"
                rel="noreferrer"
                className="button-link"
                onClick={(e) => {
                  if (!token) return;
                  e.preventDefault();
                  downloadCsv();
                }}
              >
                Export CSV
              </a>
              <EvaluationTable rows={evaluations} />
            </Section>
          ) : null}
        </>
      ) : null}

      {role === "SUPERVISOR" ? (
        <>
          <SupervisorCreateEvaluation
            token={token}
            users={users}
            levels={levels}
            skills={skills}
            onCreated={() => {
              listSupervisorEvaluations(token).then(setEvaluations).catch((e: Error) => setError(e.message));
            }}
          />
          <Section title="My Evaluations">
            <EvaluationTable rows={evaluations} />
          </Section>
        </>
      ) : null}

      {role === "INSTRUCTOR" ? (
        <Section title="My Evaluations">
          <EvaluationTable rows={evaluations} />
        </Section>
      ) : null}
    </main>
  );
}

function ManagerUsers({
  token,
  users,
  onCreated
}: {
  token: string;
  users: User[];
  onCreated: (user: User) => void;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("INSTRUCTOR");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const user = await createUser(token, { name, email, password, role, active: true });
    onCreated(user);
    setName("");
    setEmail("");
    setPassword("");
  }

  return (
    <Section title="Users">
      <form className="form inline" onSubmit={onSubmit}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="name" required />
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="email"
          type="email"
          required
        />
        <input
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="password (8+ chars)"
          minLength={8}
          type="password"
          required
        />
        <select value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
          <option value="MANAGER">MANAGER</option>
          <option value="SUPERVISOR">SUPERVISOR</option>
          <option value="INSTRUCTOR">INSTRUCTOR</option>
        </select>
        <button type="submit">Add user</button>
      </form>
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Role</th>
            <th>Active</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.name}</td>
              <td>{u.email}</td>
              <td>{u.role}</td>
              <td>{u.active ? "yes" : "no"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
  );
}

function ManagerLevels({
  token,
  levels,
  onCreated
}: {
  token: string;
  levels: Level[];
  onCreated: (level: Level) => void;
}) {
  const [name, setName] = useState("");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const level = await createLevel(token, { name, active: true });
    onCreated(level);
    setName("");
  }

  return (
    <Section title="Levels">
      <form className="form inline" onSubmit={onSubmit}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="level name" required />
        <button type="submit">Add level</button>
      </form>
      <ul>
        {levels.map((level) => (
          <li key={level.id}>
            {level.name} ({level.active ? "active" : "inactive"})
          </li>
        ))}
      </ul>
    </Section>
  );
}

function ManagerSkills({
  token,
  levels,
  skills,
  onCreated
}: {
  token: string;
  levels: Level[];
  skills: Skill[];
  onCreated: (skill: Skill) => void;
}) {
  const [name, setName] = useState("");
  const [levelId, setLevelId] = useState<number>(levels[0]?.id ?? 0);

  useEffect(() => {
    if (!levelId && levels.length > 0) setLevelId(levels[0].id);
  }, [levelId, levels]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const skill = await createSkill(token, { name, level_id: levelId, active: true });
    onCreated(skill);
    setName("");
  }

  return (
    <Section title="Skills">
      <form className="form inline" onSubmit={onSubmit}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="skill name" required />
        <select value={levelId} onChange={(e) => setLevelId(Number(e.target.value))}>
          {levels.map((level) => (
            <option key={level.id} value={level.id}>
              {level.name}
            </option>
          ))}
        </select>
        <button type="submit">Add skill</button>
      </form>
      <ul>
        {skills.map((skill) => (
          <li key={skill.id}>
            {skill.name} (level {skill.level_id})
          </li>
        ))}
      </ul>
    </Section>
  );
}

function SupervisorCreateEvaluation({
  token,
  users,
  levels,
  skills,
  onCreated
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

  const levelSkills = skills.filter((x) => x.level_id === levelId);

  useEffect(() => {
    if (users.length > 0 && !instructorId) setInstructorId(users[0].id);
  }, [instructorId, users]);

  useEffect(() => {
    if (levels.length > 0 && !levelId) setLevelId(levels[0].id);
  }, [levelId, levels]);

  useEffect(() => {
    if (levelSkills.length > 0) setSkillId(levelSkills[0].id);
  }, [levelId]);

  useEffect(() => {
    if (!levelId || !skillId) {
      setCriteria([]);
      setRatings({});
      return;
    }
    resolveSupervisorTemplate(token, levelId, skillId)
      .then((template) => {
        setCriteria(template.attributes);
        const nextRatings: Record<number, number> = {};
        for (const item of template.attributes) nextRatings[item.attribute_id] = 2;
        setRatings(nextRatings);
      })
      .catch(() => {
        setCriteria([]);
        setRatings({});
      });
  }, [token, levelId, skillId]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await createSupervisorEvaluation(token, {
      instructor_id: instructorId,
      level_id: levelId,
      skill_id: skillId,
      session_label: sessionLabel,
      session_date: sessionDate,
      notes,
      ratings: criteria.map((criterion) => ({
        attribute_id: criterion.attribute_id,
        rating_value: ratings[criterion.attribute_id] ?? 2
      }))
    });
    setSessionLabel("");
    setSessionDate("");
    setNotes("");
    onCreated();
  }

  return (
    <Section title="Create Evaluation">
      <form className="form" onSubmit={onSubmit}>
        <label>
          Instructor
          <select value={instructorId} onChange={(e) => setInstructorId(Number(e.target.value))}>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Level
          <select value={levelId} onChange={(e) => setLevelId(Number(e.target.value))}>
            {levels.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Skill
          <select value={skillId} onChange={(e) => setSkillId(Number(e.target.value))}>
            {levelSkills.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Session Label
          <input value={sessionLabel} onChange={(e) => setSessionLabel(e.target.value)} required />
        </label>
        <label>
          Session Date
          <input
            value={sessionDate}
            onChange={(e) => setSessionDate(e.target.value)}
            type="date"
            required
          />
        </label>
        <label>
          Notes
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
        <fieldset>
          <legend>Ratings</legend>
          <p>Default selection is 2 (Meets) for each criterion.</p>
          {criteria.map((criterion) => (
            <label key={criterion.attribute_id} className="inline-rating">
              <span>{criterion.attribute_name}</span>
              <select
                value={ratings[criterion.attribute_id] ?? 2}
                onChange={(e) =>
                  setRatings((prev) => ({
                    ...prev,
                    [criterion.attribute_id]: Number(e.target.value)
                  }))
                }
              >
                <option value={1}>1 Remediate</option>
                <option value={2}>2 Meets</option>
                <option value={3}>3 Exceeds</option>
              </select>
            </label>
          ))}
          {criteria.length === 0 ? (
            <p className="error">No template criteria found for selected level/skill. Cannot save draft.</p>
          ) : null}
        </fieldset>
        <button type="submit" disabled={criteria.length === 0}>
          Save Draft
        </button>
      </form>
    </Section>
  );
}

function EvaluationTable({ rows }: { rows: EvaluationSummary[] }) {
  return (
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Instructor</th>
          <th>Supervisor</th>
          <th>Level</th>
          <th>Skill</th>
          <th>Session</th>
          <th>Date</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id}>
            <td>{row.id}</td>
            <td>{row.instructor_name}</td>
            <td>{row.supervisor_name}</td>
            <td>{row.level_name}</td>
            <td>{row.skill_name}</td>
            <td>{row.session_label}</td>
            <td>{row.session_date}</td>
            <td>{row.status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ManagerDashboard({
  rows,
  onGo,
  onConfigureTemplates,
  onExport
}: {
  rows: EvaluationSummary[];
  onGo: (tab: AppTab) => void;
  onConfigureTemplates: () => void;
  onExport: () => void;
}) {
  const recent = rows.slice(0, 8);
  return (
    <Section title="Manager Dashboard">
      <div className="tabs">
        <button onClick={() => onGo("users")}>Manage Users</button>
        <button onClick={onConfigureTemplates}>Configure Templates</button>
        <button onClick={() => onGo("levels")}>Manage Levels</button>
        <button onClick={() => onGo("skills")}>Manage Skills</button>
        <button onClick={() => onGo("evaluations")}>All Evaluations</button>
        <button onClick={onExport}>Export/Email Evaluations</button>
      </div>
      <h3>Recently Completed Evaluations</h3>
      <table>
        <thead>
          <tr>
            <th>Instructor</th>
            <th>Supervisor</th>
            <th>Level</th>
            <th>Completion</th>
            <th>Summary</th>
            <th>Edited</th>
          </tr>
        </thead>
        <tbody>
          {recent.map((row) => (
            <tr key={row.id}>
              <td>{row.instructor_name}</td>
              <td>{row.supervisor_name}</td>
              <td>{row.level_name}</td>
              <td>{row.submitted_at ?? "-"}</td>
              <td>{row.session_label}</td>
              <td>-</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
  );
}
