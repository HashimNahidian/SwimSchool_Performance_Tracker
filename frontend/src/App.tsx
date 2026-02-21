<<<<<<< HEAD
import { FormEvent, ReactNode, useMemo, useEffect, useState } from "react";

import {
  createAttribute,
  createLevel,
  createSkill,
  createSupervisorEvaluation,
  createUser,
  exportEvaluationsCsvUrl,
  listAttributes,
  listInstructorEvaluations,
  listLevels,
  listManagerEvaluations,
  listSkills,
  listSupervisorEvaluations,
  listUsers,
  login,
  logout,
  me,
  refresh
} from "./api";
import type { Attribute, EvaluationSummary, Level, Skill, User, UserRole } from "./types";

type AppTab = "users" | "levels" | "skills" | "attributes" | "evaluations";

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

export default function App() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState<string | null>(localStorage.getItem("token"));
  const [refreshToken, setRefreshToken] = useState<string | null>(
    localStorage.getItem("refresh_token")
  );
  const [meUser, setMeUser] = useState<User | null>(null);
  const [error, setError] = useState<string>("");
  const [tab, setTab] = useState<AppTab>("users");

  const [users, setUsers] = useState<User[]>([]);
  const [levels, setLevels] = useState<Level[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [attributes, setAttributes] = useState<Attribute[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationSummary[]>([]);

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
        listAttributes(token),
        listManagerEvaluations(token)
      ])
        .then(([nextUsers, nextLevels, nextSkills, nextAttributes, nextEvaluations]) => {
          setUsers(nextUsers);
          setLevels(nextLevels);
          setSkills(nextSkills);
          setAttributes(nextAttributes);
          setEvaluations(nextEvaluations);
        })
        .catch((e: Error) => setError(e.message));
    } else if (role === "SUPERVISOR") {
      Promise.all([listUsers(token), listLevels(token), listSkills(token), listAttributes(token), listSupervisorEvaluations(token)])
        .then(([nextUsers, nextLevels, nextSkills, nextAttributes, nextEvaluations]) => {
          setUsers(nextUsers.filter((x) => x.role === "INSTRUCTOR"));
          setLevels(nextLevels);
          setSkills(nextSkills);
          setAttributes(nextAttributes);
          setEvaluations(nextEvaluations);
        })
        .catch((e: Error) => setError(e.message));
    } else {
      listInstructorEvaluations(token)
        .then(setEvaluations)
        .catch((e: Error) => setError(e.message));
    }
  }, [role, token]);

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
            {(["users", "levels", "skills", "attributes", "evaluations"] as AppTab[]).map(
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
          {tab === "attributes" ? (
            <ManagerAttributes
              token={token}
              attributes={attributes}
              onCreated={(attribute) => setAttributes((prev) => [...prev, attribute])}
            />
          ) : null}
          {tab === "evaluations" ? (
            <Section title="All Evaluations">
              <a
                href={exportEvaluationsCsvUrl()}
                target="_blank"
                rel="noreferrer"
                className="button-link"
                onClick={(e) => {
                  if (!token) return;
                  e.preventDefault();
                  fetch(exportEvaluationsCsvUrl(), { headers: authHeader }).then(async (resp) => {
                    const blob = await resp.blob();
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = "evaluations.csv";
                    link.click();
                    URL.revokeObjectURL(url);
                  });
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
            attributes={attributes}
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

function ManagerAttributes({
  token,
  attributes,
  onCreated
}: {
  token: string;
  attributes: Attribute[];
  onCreated: (attribute: Attribute) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const attribute = await createAttribute(token, { name, description, active: true });
    onCreated(attribute);
    setName("");
    setDescription("");
  }

  return (
    <Section title="Attributes">
      <form className="form inline" onSubmit={onSubmit}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="attribute name" required />
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="description"
        />
        <button type="submit">Add attribute</button>
      </form>
      <ul>
        {attributes.map((attribute) => (
          <li key={attribute.id}>
            {attribute.name} {attribute.description ? `- ${attribute.description}` : ""}
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
  attributes,
  onCreated
}: {
  token: string;
  users: User[];
  levels: Level[];
  skills: Skill[];
  attributes: Attribute[];
  onCreated: () => void;
}) {
  const [instructorId, setInstructorId] = useState<number>(users[0]?.id ?? 0);
  const [levelId, setLevelId] = useState<number>(levels[0]?.id ?? 0);
  const [skillId, setSkillId] = useState<number>(0);
  const [sessionLabel, setSessionLabel] = useState("");
  const [sessionDate, setSessionDate] = useState("");
  const [notes, setNotes] = useState("");
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

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await createSupervisorEvaluation(token, {
      instructor_id: instructorId,
      level_id: levelId,
      skill_id: skillId,
      session_label: sessionLabel,
      session_date: sessionDate,
      notes,
      ratings: Object.entries(ratings).map(([attribute_id, rating_value]) => ({
        attribute_id: Number(attribute_id),
        rating_value
      }))
    });
    setSessionLabel("");
    setSessionDate("");
    setNotes("");
    setRatings({});
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
          {attributes.map((a) => (
            <label key={a.id} className="inline-rating">
              <span>{a.name}</span>
              <select
                value={ratings[a.id] ?? ""}
                onChange={(e) =>
                  setRatings((prev) => ({ ...prev, [a.id]: Number(e.target.value) }))
                }
              >
                <option value="">-</option>
                <option value={1}>1 Remediate</option>
                <option value={2}>2 Meets</option>
                <option value={3}>3 Exceeds</option>
              </select>
            </label>
          ))}
        </fieldset>
        <button type="submit">Save Draft</button>
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
=======
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { EvaluationDetailPage } from "./EvaluationDetailPage";
import { InstructorPage } from "./InstructorPage";
import { Layout } from "./Layout";
import { LoginPage } from "./LoginPage";
import { ManagerPage } from "./ManagerPage";
import { ProtectedRoute } from "./ProtectedRoute";
import { SupervisorPage } from "./SupervisorPage";

function RoleHomeRedirect() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={`/${user.role.toLowerCase()}`} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<Layout />}>
        <Route index element={<RoleHomeRedirect />} />
        <Route
          path="manager"
          element={
            <ProtectedRoute allowedRoles={["MANAGER"]}>
              <ManagerPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="supervisor"
          element={
            <ProtectedRoute allowedRoles={["SUPERVISOR"]}>
              <SupervisorPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="instructor"
          element={
            <ProtectedRoute allowedRoles={["INSTRUCTOR"]}>
              <InstructorPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="evaluations/:evaluationId"
          element={
            <ProtectedRoute allowedRoles={["MANAGER", "SUPERVISOR", "INSTRUCTOR"]}>
              <EvaluationDetailPage />
            </ProtectedRoute>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
>>>>>>> origin/main
  );
}
