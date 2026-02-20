import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest } from "./api";
import { useAuth } from "./auth";
import type { Attribute, Evaluation, Level, Skill, Template, User } from "./types";

export function SupervisorPage() {
  const { token } = useAuth();
  const [instructors, setInstructors] = useState<User[]>([]);
  const [levels, setLevels] = useState<Level[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [attributes, setAttributes] = useState<Attribute[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [drafts, setDrafts] = useState<Evaluation[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [instructorId, setInstructorId] = useState("");
  const [levelId, setLevelId] = useState("");
  const [skillId, setSkillId] = useState("");
  const [sessionDate, setSessionDate] = useState("");
  const [sessionLabel, setSessionLabel] = useState("");
  const [notes, setNotes] = useState("");
  const [ratings, setRatings] = useState<Record<number, number>>({});

  const selectedTemplate = useMemo(
    () =>
      templates.find(
        (template) =>
          template.level_id === (levelId ? Number(levelId) : null) &&
          template.skill_id === (skillId ? Number(skillId) : null)
      ) ??
      templates.find((template) => template.level_id === (levelId ? Number(levelId) : null)) ??
      templates[0],
    [templates, levelId, skillId]
  );

  const attributeMap = new Map(attributes.map((attribute) => [attribute.id, attribute]));

  async function loadData() {
    if (!token) return;
    try {
      const [usersData, levelsData, skillsData, attributesData, templatesData, draftsData] =
        await Promise.all([
          apiRequest<User[]>("/instructors", {}, token),
          apiRequest<Level[]>("/levels?active=true", {}, token),
          apiRequest<Skill[]>("/skills?active=true", {}, token),
          apiRequest<Attribute[]>("/attributes?active=true", {}, token),
          apiRequest<Template[]>("/templates?active=true", {}, token),
          apiRequest<Evaluation[]>("/supervisor/evaluations?status=DRAFT", {}, token)
        ]);
      setInstructors(usersData);
      setLevels(levelsData);
      setSkills(skillsData);
      setAttributes(attributesData);
      setTemplates(templatesData);
      setDrafts(draftsData);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  useEffect(() => {
    void loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (!selectedTemplate) return;
    const next: Record<number, number> = {};
    selectedTemplate.template_attributes.forEach((attribute) => {
      next[attribute.attribute_id] = 2;
    });
    setRatings(next);
  }, [selectedTemplate?.id]);

  async function createDraft(event: FormEvent) {
    event.preventDefault();
    if (!token || !instructorId || !sessionDate) return;
    const ratingPayload = Object.entries(ratings).map(([attributeId, value]) => ({
      attribute_id: Number(attributeId),
      rating_value: value
    }));

    await apiRequest<Evaluation>(
      "/evaluations/draft",
      {
        method: "POST",
        body: JSON.stringify({
          instructor_id: Number(instructorId),
          level_id: levelId ? Number(levelId) : null,
          skill_id: skillId ? Number(skillId) : null,
          session_label: sessionLabel || null,
          session_date: sessionDate,
          notes: notes || null,
          ratings: ratingPayload
        })
      },
      token
    );
    setSessionLabel("");
    setNotes("");
    await loadData();
  }

  async function submitDraft(evaluationId: number) {
    if (!token) return;
    await apiRequest<Evaluation>(`/evaluations/${evaluationId}/submit`, { method: "POST" }, token);
    await loadData();
  }

  function setRating(attributeId: number, value: number) {
    setRatings((prev) => ({ ...prev, [attributeId]: value }));
  }

  const filteredSkills = levelId
    ? skills.filter((skill) => skill.level_id === Number(levelId))
    : skills;

  return (
    <div className="stack">
      <h2>Supervisor Dashboard</h2>
      {error && <p className="error">{error}</p>}

      <section className="panel">
        <h3>Create Evaluation Draft</h3>
        <form onSubmit={createDraft} className="stack">
          <div className="inline-form">
            <select value={instructorId} onChange={(e) => setInstructorId(e.target.value)} required>
              <option value="">Select instructor</option>
              {instructors.map((instructor) => (
                <option key={instructor.id} value={instructor.id}>
                  {instructor.name}
                </option>
              ))}
            </select>
            <select value={levelId} onChange={(e) => setLevelId(e.target.value)}>
              <option value="">No level</option>
              {levels.map((level) => (
                <option key={level.id} value={level.id}>
                  {level.name}
                </option>
              ))}
            </select>
            <select value={skillId} onChange={(e) => setSkillId(e.target.value)}>
              <option value="">No skill</option>
              {filteredSkills.map((skill) => (
                <option key={skill.id} value={skill.id}>
                  {skill.name}
                </option>
              ))}
            </select>
            <input type="date" value={sessionDate} onChange={(e) => setSessionDate(e.target.value)} required />
          </div>
          <input
            value={sessionLabel}
            onChange={(e) => setSessionLabel(e.target.value)}
            placeholder="Session label"
          />
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Notes" rows={3} />
          <div className="stack">
            <strong>Ratings</strong>
            {(selectedTemplate?.template_attributes || []).map((templateAttribute) => (
              <label key={templateAttribute.attribute_id} className="inline-form">
                <span>{attributeMap.get(templateAttribute.attribute_id)?.name ?? templateAttribute.attribute_id}</span>
                <select
                  value={ratings[templateAttribute.attribute_id] ?? 2}
                  onChange={(e) => setRating(templateAttribute.attribute_id, Number(e.target.value))}
                >
                  <option value={1}>1 - Remediate</option>
                  <option value={2}>2 - Meets</option>
                  <option value={3}>3 - Exceeds</option>
                </select>
              </label>
            ))}
            {!selectedTemplate && (
              <p>No matching template found. Create one in manager dashboard first.</p>
            )}
          </div>
          <button type="submit">Save Draft</button>
        </form>
      </section>

      <section className="panel">
        <h3>My Drafts</h3>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Instructor</th>
              <th>Date</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {drafts.map((draft) => (
              <tr key={draft.id}>
                <td>{draft.id}</td>
                <td>{instructors.find((instructor) => instructor.id === draft.instructor_id)?.name ?? draft.instructor_id}</td>
                <td>{draft.session_date}</td>
                <td>{draft.status}</td>
                <td>
                  <button onClick={() => submitDraft(draft.id)}>Submit</button>
                  <Link to={`/evaluations/${draft.id}`}>View</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
