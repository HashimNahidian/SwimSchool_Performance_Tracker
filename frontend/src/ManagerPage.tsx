import { FormEvent, useEffect, useState } from "react";
import { apiBlob, apiRequest } from "./api";
import { useAuth } from "./auth";
import type { Attribute, Evaluation, Level, Skill, Template, User } from "./types";

export function ManagerPage() {
  const { token } = useAuth();
  const [levels, setLevels] = useState<Level[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [attributes, setAttributes] = useState<Attribute[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [levelName, setLevelName] = useState("");
  const [skillName, setSkillName] = useState("");
  const [skillLevelId, setSkillLevelId] = useState("");
  const [attributeName, setAttributeName] = useState("");
  const [attributeDescription, setAttributeDescription] = useState("");
  const [templateName, setTemplateName] = useState("");
  const [templateLevelId, setTemplateLevelId] = useState("");
  const [templateSkillId, setTemplateSkillId] = useState("");
  const [templateAttributeIds, setTemplateAttributeIds] = useState<number[]>([]);
  const [evalDateFrom, setEvalDateFrom] = useState("");
  const [evalDateTo, setEvalDateTo] = useState("");
  const [evalStatus, setEvalStatus] = useState("");
  const [evalInstructorId, setEvalInstructorId] = useState("");
  const [evalSupervisorId, setEvalSupervisorId] = useState("");
  const [evalSortBy, setEvalSortBy] = useState("created_at");
  const [evalSortDir, setEvalSortDir] = useState("desc");
  const [evalLimit, setEvalLimit] = useState(25);
  const [evalOffset, setEvalOffset] = useState(0);

  function buildEvalQuery(includePagination: boolean): string {
    const params = new URLSearchParams();
    if (evalDateFrom) params.set("date_from", evalDateFrom);
    if (evalDateTo) params.set("date_to", evalDateTo);
    if (evalStatus) params.set("status", evalStatus);
    if (evalInstructorId) params.set("instructor_id", evalInstructorId);
    if (evalSupervisorId) params.set("supervisor_id", evalSupervisorId);
    params.set("sort_by", evalSortBy);
    params.set("sort_dir", evalSortDir);
    if (includePagination) {
      params.set("limit", String(evalLimit));
      params.set("offset", String(evalOffset));
    }
    const query = params.toString();
    return query ? `?${query}` : "";
  }

  async function loadData() {
    if (!token) return;
    try {
      const [levelData, skillData, attributeData, templateData, evalData, userData] =
        await Promise.all([
          apiRequest<Level[]>("/levels", {}, token),
          apiRequest<Skill[]>("/skills", {}, token),
          apiRequest<Attribute[]>("/attributes", {}, token),
          apiRequest<Template[]>("/templates", {}, token),
          apiRequest<Evaluation[]>(`/manager/evaluations${buildEvalQuery(true)}`, {}, token),
          apiRequest<User[]>("/users", {}, token)
        ]);
      setLevels(levelData);
      setSkills(skillData);
      setAttributes(attributeData);
      setTemplates(templateData);
      setEvaluations(evalData);
      setUsers(userData);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  useEffect(() => {
    void loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, evalDateFrom, evalDateTo, evalStatus, evalInstructorId, evalSupervisorId, evalSortBy, evalSortDir, evalLimit, evalOffset]);

  async function createLevel(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    await apiRequest("/levels", {
      method: "POST",
      body: JSON.stringify({ name: levelName, active: true })
    }, token);
    setLevelName("");
    await loadData();
  }

  async function toggleLevel(level: Level) {
    if (!token) return;
    await apiRequest(`/levels/${level.id}`, {
      method: "PATCH",
      body: JSON.stringify({ active: !level.active })
    }, token);
    await loadData();
  }

  async function createSkill(event: FormEvent) {
    event.preventDefault();
    if (!token || !skillLevelId) return;
    await apiRequest("/skills", {
      method: "POST",
      body: JSON.stringify({ name: skillName, level_id: Number(skillLevelId), active: true })
    }, token);
    setSkillName("");
    await loadData();
  }

  async function toggleSkill(skill: Skill) {
    if (!token) return;
    await apiRequest(`/skills/${skill.id}`, {
      method: "PATCH",
      body: JSON.stringify({ active: !skill.active })
    }, token);
    await loadData();
  }

  async function createAttribute(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    await apiRequest("/attributes", {
      method: "POST",
      body: JSON.stringify({
        name: attributeName,
        description: attributeDescription || null,
        active: true
      })
    }, token);
    setAttributeName("");
    setAttributeDescription("");
    await loadData();
  }

  async function toggleAttribute(attribute: Attribute) {
    if (!token) return;
    await apiRequest(`/attributes/${attribute.id}`, {
      method: "PATCH",
      body: JSON.stringify({ active: !attribute.active })
    }, token);
    await loadData();
  }

  async function createTemplate(event: FormEvent) {
    event.preventDefault();
    if (!token || templateAttributeIds.length === 0) return;
    await apiRequest("/templates", {
      method: "POST",
      body: JSON.stringify({
        name: templateName,
        level_id: templateLevelId ? Number(templateLevelId) : null,
        skill_id: templateSkillId ? Number(templateSkillId) : null,
        active: true,
        attribute_ids: templateAttributeIds
      })
    }, token);
    setTemplateName("");
    setTemplateAttributeIds([]);
    await loadData();
  }

  async function toggleTemplate(template: Template) {
    if (!token) return;
    await apiRequest(`/templates/${template.id}`, {
      method: "PATCH",
      body: JSON.stringify({ active: !template.active })
    }, token);
    await loadData();
  }

  async function exportCsv() {
    if (!token) return;
    const blob = await apiBlob(`/exports/evaluations.csv${buildEvalQuery(false)}`, {}, token);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "evaluations.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  function onTemplateAttrToggle(attributeId: number, checked: boolean) {
    setTemplateAttributeIds((prev) =>
      checked ? [...prev, attributeId] : prev.filter((id) => id !== attributeId)
    );
  }

  const usersById = new Map(users.map((user) => [user.id, user]));
  const supervisors = users.filter((user) => user.role === "SUPERVISOR");
  const instructors = users.filter((user) => user.role === "INSTRUCTOR");

  return (
    <div className="stack">
      <h2>Manager Dashboard</h2>
      {error && <p className="error">{error}</p>}

      <section className="panel">
        <h3>Levels</h3>
        <form onSubmit={createLevel} className="inline-form">
          <input
            value={levelName}
            onChange={(e) => setLevelName(e.target.value)}
            placeholder="New level name"
            required
          />
          <button type="submit">Add Level</button>
        </form>
        <ul>
          {levels.map((level) => (
            <li key={level.id}>
              {level.name} ({level.active ? "Active" : "Inactive"}){" "}
              <button onClick={() => toggleLevel(level)}>{level.active ? "Deactivate" : "Activate"}</button>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <h3>Skills</h3>
        <form onSubmit={createSkill} className="inline-form">
          <select value={skillLevelId} onChange={(e) => setSkillLevelId(e.target.value)} required>
            <option value="">Select level</option>
            {levels.map((level) => (
              <option key={level.id} value={level.id}>
                {level.name}
              </option>
            ))}
          </select>
          <input
            value={skillName}
            onChange={(e) => setSkillName(e.target.value)}
            placeholder="New skill name"
            required
          />
          <button type="submit">Add Skill</button>
        </form>
        <ul>
          {skills.map((skill) => (
            <li key={skill.id}>
              {skill.name} ({levels.find((level) => level.id === skill.level_id)?.name ?? "Unknown level"}) -{" "}
              {skill.active ? "Active" : "Inactive"}{" "}
              <button onClick={() => toggleSkill(skill)}>{skill.active ? "Deactivate" : "Activate"}</button>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <h3>Attributes</h3>
        <form onSubmit={createAttribute} className="inline-form">
          <input
            value={attributeName}
            onChange={(e) => setAttributeName(e.target.value)}
            placeholder="Attribute name"
            required
          />
          <input
            value={attributeDescription}
            onChange={(e) => setAttributeDescription(e.target.value)}
            placeholder="Description"
          />
          <button type="submit">Add Attribute</button>
        </form>
        <ul>
          {attributes.map((attribute) => (
            <li key={attribute.id}>
              {attribute.name} ({attribute.active ? "Active" : "Inactive"}){" "}
              <button onClick={() => toggleAttribute(attribute)}>{attribute.active ? "Deactivate" : "Activate"}</button>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <h3>Template Builder</h3>
        <form onSubmit={createTemplate} className="stack">
          <div className="inline-form">
            <input
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              placeholder="Template name"
              required
            />
            <select value={templateLevelId} onChange={(e) => setTemplateLevelId(e.target.value)}>
              <option value="">Any level</option>
              {levels.map((level) => (
                <option key={level.id} value={level.id}>
                  {level.name}
                </option>
              ))}
            </select>
            <select value={templateSkillId} onChange={(e) => setTemplateSkillId(e.target.value)}>
              <option value="">Any skill</option>
              {skills.map((skill) => (
                <option key={skill.id} value={skill.id}>
                  {skill.name}
                </option>
              ))}
            </select>
          </div>
          <div className="grid">
            {attributes.map((attribute) => (
              <label key={attribute.id}>
                <input
                  type="checkbox"
                  checked={templateAttributeIds.includes(attribute.id)}
                  onChange={(e) => onTemplateAttrToggle(attribute.id, e.target.checked)}
                />
                {attribute.name}
              </label>
            ))}
          </div>
          <button type="submit">Create Template</button>
        </form>
        <ul>
          {templates.map((template) => (
            <li key={template.id}>
              {template.name} - {template.template_attributes.length} attributes -{" "}
              {template.active ? "Active" : "Inactive"}{" "}
              <button onClick={() => toggleTemplate(template)}>{template.active ? "Deactivate" : "Activate"}</button>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <h3>Global Evaluations</h3>
        <div className="inline-form">
          <input type="date" value={evalDateFrom} onChange={(e) => { setEvalOffset(0); setEvalDateFrom(e.target.value); }} />
          <input type="date" value={evalDateTo} onChange={(e) => { setEvalOffset(0); setEvalDateTo(e.target.value); }} />
          <select value={evalStatus} onChange={(e) => { setEvalOffset(0); setEvalStatus(e.target.value); }}>
            <option value="">All statuses</option>
            <option value="DRAFT">DRAFT</option>
            <option value="SUBMITTED">SUBMITTED</option>
          </select>
          <select value={evalInstructorId} onChange={(e) => { setEvalOffset(0); setEvalInstructorId(e.target.value); }}>
            <option value="">All instructors</option>
            {instructors.map((user) => (
              <option key={user.id} value={user.id}>
                {user.name}
              </option>
            ))}
          </select>
          <select value={evalSupervisorId} onChange={(e) => { setEvalOffset(0); setEvalSupervisorId(e.target.value); }}>
            <option value="">All supervisors</option>
            {supervisors.map((user) => (
              <option key={user.id} value={user.id}>
                {user.name}
              </option>
            ))}
          </select>
          <select value={evalSortBy} onChange={(e) => setEvalSortBy(e.target.value)}>
            <option value="created_at">Sort by created</option>
            <option value="session_date">Sort by session date</option>
            <option value="submitted_at">Sort by submitted at</option>
            <option value="status">Sort by status</option>
            <option value="id">Sort by id</option>
          </select>
          <select value={evalSortDir} onChange={(e) => setEvalSortDir(e.target.value)}>
            <option value="desc">Desc</option>
            <option value="asc">Asc</option>
          </select>
          <select value={evalLimit} onChange={(e) => { setEvalOffset(0); setEvalLimit(Number(e.target.value)); }}>
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
          </select>
        </div>
        <button onClick={exportCsv}>Export CSV</button>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Instructor</th>
              <th>Supervisor</th>
              <th>Date</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {evaluations.map((evaluation) => (
              <tr key={evaluation.id}>
                <td>{evaluation.id}</td>
                <td>{usersById.get(evaluation.instructor_id)?.name ?? evaluation.instructor_id}</td>
                <td>{usersById.get(evaluation.supervisor_id)?.name ?? evaluation.supervisor_id}</td>
                <td>{evaluation.session_date}</td>
                <td>{evaluation.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="inline-form">
          <button onClick={() => setEvalOffset(Math.max(0, evalOffset - evalLimit))} disabled={evalOffset === 0}>
            Previous
          </button>
          <span>Offset: {evalOffset}</span>
          <button onClick={() => setEvalOffset(evalOffset + evalLimit)} disabled={evaluations.length < evalLimit}>
            Next
          </button>
        </div>
      </section>
    </div>
  );
}
