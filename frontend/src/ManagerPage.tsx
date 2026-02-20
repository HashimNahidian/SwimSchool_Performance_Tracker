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

  async function loadData() {
    if (!token) return;
    try {
      const [levelData, skillData, attributeData, templateData, evalData, userData] =
        await Promise.all([
          apiRequest<Level[]>("/levels", {}, token),
          apiRequest<Skill[]>("/skills", {}, token),
          apiRequest<Attribute[]>("/attributes", {}, token),
          apiRequest<Template[]>("/templates", {}, token),
          apiRequest<Evaluation[]>("/manager/evaluations", {}, token),
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
  }, [token]);

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

  async function exportCsv() {
    if (!token) return;
    const blob = await apiBlob("/exports/evaluations.csv", {}, token);
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
        <ul>{levels.map((level) => <li key={level.id}>{level.name}</li>)}</ul>
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
              {skill.name} ({levels.find((level) => level.id === skill.level_id)?.name ?? "Unknown level"})
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
            <li key={attribute.id}>{attribute.name}</li>
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
              {template.name} - {template.template_attributes.length} attributes
            </li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <h3>Global Evaluations</h3>
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
      </section>
    </div>
  );
}
