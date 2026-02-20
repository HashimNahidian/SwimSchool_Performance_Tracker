import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest } from "./api";
import { useAuth } from "./auth";
import type { Evaluation, Level, Skill, TrendPoint, User } from "./types";

export function InstructorPage() {
  const { token } = useAuth();
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [levels, setLevels] = useState<Level[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [supervisors, setSupervisors] = useState<User[]>([]);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [levelId, setLevelId] = useState("");
  const [skillId, setSkillId] = useState("");
  const [supervisorId, setSupervisorId] = useState("");

  async function loadLookups() {
    if (!token) return;
    const [levelsData, skillsData, supervisorsData] = await Promise.all([
      apiRequest<Level[]>("/levels", {}, token),
      apiRequest<Skill[]>("/skills", {}, token),
      apiRequest<User[]>("/supervisors", {}, token)
    ]);
    setLevels(levelsData);
    setSkills(skillsData);
    setSupervisors(supervisorsData);
  }

  async function loadEvaluations(event?: FormEvent) {
    event?.preventDefault();
    if (!token) return;
    try {
      const params = new URLSearchParams();
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      if (levelId) params.set("level_id", levelId);
      if (skillId) params.set("skill_id", skillId);
      if (supervisorId) params.set("supervisor_id", supervisorId);
      const query = params.toString();
      const [data, trendData] = await Promise.all([
        apiRequest<Evaluation[]>(`/me/evaluations${query ? `?${query}` : ""}`, {}, token),
        apiRequest<TrendPoint[]>(`/me/evaluations/trends${query ? `?${query}` : ""}`, {}, token)
      ]);
      setEvaluations(data);
      setTrends(trendData);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  useEffect(() => {
    void loadLookups();
    void loadEvaluations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="stack">
      <h2>Instructor Dashboard</h2>
      {error && <p className="error">{error}</p>}
      <section className="panel">
        <h3>Filters</h3>
        <form onSubmit={loadEvaluations} className="inline-form">
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          <select value={levelId} onChange={(e) => setLevelId(e.target.value)}>
            <option value="">All levels</option>
            {levels.map((level) => (
              <option key={level.id} value={level.id}>
                {level.name}
              </option>
            ))}
          </select>
          <select value={skillId} onChange={(e) => setSkillId(e.target.value)}>
            <option value="">All skills</option>
            {skills.map((skill) => (
              <option key={skill.id} value={skill.id}>
                {skill.name}
              </option>
            ))}
          </select>
          <select value={supervisorId} onChange={(e) => setSupervisorId(e.target.value)}>
            <option value="">All supervisors</option>
            {supervisors.map((supervisor) => (
              <option key={supervisor.id} value={supervisor.id}>
                {supervisor.name}
              </option>
            ))}
          </select>
          <button type="submit">Apply</button>
        </form>
      </section>

      <section className="panel">
        <h3>My Evaluations</h3>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Date</th>
              <th>Status</th>
              <th>Ratings</th>
              <th>Open</th>
            </tr>
          </thead>
          <tbody>
            {evaluations.map((evaluation) => (
              <tr key={evaluation.id}>
                <td>{evaluation.id}</td>
                <td>{evaluation.session_date}</td>
                <td>{evaluation.status}</td>
                <td>{evaluation.ratings.length}</td>
                <td>
                  <Link to={`/evaluations/${evaluation.id}`}>Details</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel">
        <h3>Trend Analytics</h3>
        <table>
          <thead>
            <tr>
              <th>Period</th>
              <th>Evaluations</th>
              <th>Avg Rating</th>
            </tr>
          </thead>
          <tbody>
            {trends.map((trend) => (
              <tr key={trend.period}>
                <td>{trend.period}</td>
                <td>{trend.evaluation_count}</td>
                <td>{trend.average_rating.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
