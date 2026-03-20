import { type FormEvent, useState } from "react";
import { createSupervisorScheduledEvaluation, deleteSupervisorScheduledEvaluation, updateSupervisorScheduledEvaluation } from "../api";
import type { EvaluationSummary, ScheduledEvaluation, ScheduledEvaluationStatus } from "../types";
import { SupervisorCreateEvaluation, SupervisorReevaluationPanel, type ReevaluationPrefill, useSupervisorData } from "./supervisor/shared";

export function SupervisorPage() {
  const {
    token,
    user,
    error,
    users,
    levels,
    skills,
    scheduledEvaluations,
    filteredAssignedEvaluations,
    filters,
    setFilters,
    refreshData,
    handleCreated,
  } = useSupervisorData();
  const [showCreate, setShowCreate] = useState(false);
  const [showScheduleForm, setShowScheduleForm] = useState(false);
  const [selectedReeval, setSelectedReeval] = useState<ReevaluationPrefill | null>(null);
  const [scheduleForm, setScheduleForm] = useState({
    instructorId: "",
    levelId: "",
    skillId: "",
    targetDate: new Date().toISOString().slice(0, 10),
    notes: "",
  });
  const [editingScheduleId, setEditingScheduleId] = useState<number | null>(null);
  const [scheduleError, setScheduleError] = useState("");

  if (!token) return null;

  const availableScheduleSkills = skills.filter((skill) => !scheduleForm.levelId || skill.level_id === Number(scheduleForm.levelId));
  const activeScheduled = scheduledEvaluations.filter((item) => item.status !== "COMPLETED" && item.status !== "CANCELED");
  const pendingCount = activeScheduled.filter((item) => item.status === "PENDING").length;
  const overdueCount = activeScheduled.filter((item) => item.status !== "COMPLETED" && item.target_date < new Date().toISOString().slice(0, 10)).length;
  const completedCount = scheduledEvaluations.filter((item) => item.status === "COMPLETED").length;

  function handleAssignedReevaluation(evaluation: EvaluationSummary) {
    setSelectedReeval({
      evaluationId: evaluation.id,
      instructorId: evaluation.instructor_id,
      levelId: evaluation.level_id,
      skillId: evaluation.skill_id,
      sourceEvalId: evaluation.id,
      mode: "reevaluation",
    });
    setShowCreate(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleCompleteScheduled(schedule: ScheduledEvaluation) {
    setSelectedReeval({
      evaluationId: schedule.id,
      instructorId: schedule.instructor_id,
      levelId: schedule.level_id,
      skillId: schedule.skill_id,
      scheduledEvaluationId: schedule.id,
      mode: "scheduled",
      helperText: `Scheduled for ${schedule.skill_name} on ${new Date(schedule.target_date + "T00:00:00").toLocaleDateString()}`,
    });
    setShowCreate(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function submitSchedule(e: FormEvent) {
    e.preventDefault();
    if (!token || !scheduleForm.instructorId || !scheduleForm.skillId || !scheduleForm.targetDate) return;
    setScheduleError("");
    try {
      const payload = {
        instructor_id: Number(scheduleForm.instructorId),
        skill_id: Number(scheduleForm.skillId),
        target_date: scheduleForm.targetDate,
        notes: scheduleForm.notes.trim() || null,
      };
      if (editingScheduleId) {
        await updateSupervisorScheduledEvaluation(token, editingScheduleId, payload);
      } else {
        await createSupervisorScheduledEvaluation(token, payload);
      }
      setEditingScheduleId(null);
      setScheduleForm({
        instructorId: "",
        levelId: "",
        skillId: "",
        targetDate: new Date().toISOString().slice(0, 10),
        notes: "",
      });
      setShowScheduleForm(false);
      refreshData();
    } catch (err) {
      setScheduleError((err as Error).message);
    }
  }

  function startEditSchedule(schedule: ScheduledEvaluation) {
    setEditingScheduleId(schedule.id);
    setShowScheduleForm(true);
    setScheduleForm({
      instructorId: String(schedule.instructor_id),
      levelId: String(schedule.level_id),
      skillId: String(schedule.skill_id),
      targetDate: schedule.target_date,
      notes: schedule.notes ?? "",
    });
  }

  async function updateScheduleStatus(schedule: ScheduledEvaluation, status: ScheduledEvaluationStatus) {
    if (!token) return;
    try {
      await updateSupervisorScheduledEvaluation(token, schedule.id, { status });
      refreshData();
    } catch (err) {
      setScheduleError((err as Error).message);
    }
  }

  async function removeSchedule(id: number) {
    if (!token) return;
    try {
      await deleteSupervisorScheduledEvaluation(token, id);
      refreshData();
    } catch (err) {
      setScheduleError((err as Error).message);
    }
  }

  return (
    <>
      {error && <p className="error">{error}</p>}

      <div className="page-heading">
        <h1 className="page-title">Welcome back, {user?.full_name ?? "Supervisor"}</h1>
        <p className="page-subtitle">Create new evaluations and work through reevaluation requests.</p>
      </div>

      <div className="stat-cards supervisor-stat-cards">
        <div className="stat-card">
          <div className="stat-card-value" style={{ color: "#023e8a" }}>{pendingCount}</div>
          <div className="stat-card-label">Scheduled Evaluations</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-value" style={{ color: "#c2550a" }}>{overdueCount}</div>
          <div className="stat-card-label">Overdue</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-value" style={{ color: "#2563eb" }}>{completedCount}</div>
          <div className="stat-card-label">Completed</div>
        </div>
      </div>

      <div style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", gap: 8, padding: 8, alignItems: "center" }}>
          <button
            className="btn-add"
            type="button"
            aria-expanded={showScheduleForm}
            aria-label="Schedule Evaluation"
            onClick={() => setShowScheduleForm((prev) => !prev)}
          >
            Schedule Evaluation
          </button>
          <button
            className="btn-add"
            type="button"
            aria-expanded={showCreate}
            aria-label="Create Evaluation"
            onClick={() => setShowCreate((prev) => !prev)}
          >
            Create Evaluation
          </button>
        </div>

        <div
          className="card"
          aria-hidden={!showScheduleForm}
          style={{
            display: showScheduleForm ? "block" : "none",
            overflow: "hidden",
            marginTop: 8,
          }}
        >
          <div style={{ marginBottom: 12 }}>
            <h2 style={{ marginBottom: 0 }}>Schedule Evaluation</h2>
          </div>
          <form className="form" onSubmit={submitSchedule}>
            <label>
              Instructor
              <select
                required
                value={scheduleForm.instructorId}
                onChange={(e) => setScheduleForm((prev) => ({ ...prev, instructorId: e.target.value }))}
              >
                <option value="">Select instructor</option>
                {users.map((userItem) => (
                  <option key={userItem.id} value={userItem.id}>{userItem.full_name}</option>
                ))}
              </select>
            </label>
            <label>
              Level
              <select
                value={scheduleForm.levelId}
                onChange={(e) => setScheduleForm((prev) => ({ ...prev, levelId: e.target.value, skillId: "" }))}
              >
                <option value="">Select level</option>
                {levels.map((level) => (
                  <option key={level.id} value={level.id}>{level.name}</option>
                ))}
              </select>
            </label>
            <label>
              Skill
              <select
                value={scheduleForm.skillId}
                onChange={(e) => setScheduleForm((prev) => ({ ...prev, skillId: e.target.value }))}
              >
                <option value="">Select skill</option>
                {availableScheduleSkills.map((skill) => (
                  <option key={skill.id} value={skill.id}>{skill.name}</option>
                ))}
              </select>
            </label>
            <label>
              Target Date
              <input
                type="date"
                value={scheduleForm.targetDate}
                onChange={(e) => setScheduleForm((prev) => ({ ...prev, targetDate: e.target.value }))}
              />
            </label>
            <label>
              Notes
              <textarea
                value={scheduleForm.notes}
                onChange={(e) => setScheduleForm((prev) => ({ ...prev, notes: e.target.value }))}
                placeholder="Optional assignment notes..."
              />
            </label>
            {scheduleError && <p className="error">{scheduleError}</p>}
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button type="submit">{editingScheduleId ? "Update Assignment" : "Schedule Evaluation"}</button>
              {editingScheduleId && (
                <button
                  type="button"
                  className="btn-add"
                  onClick={() => {
                    setEditingScheduleId(null);
                    setScheduleForm({
                      instructorId: "",
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

          {activeScheduled.length > 0 ? (
            <table style={{ marginTop: 16 }}>
              <thead>
                <tr>
                  <th>Instructor</th>
                  <th>Level</th>
                  <th>Skill</th>
                  <th>Target Date</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {activeScheduled.map((schedule) => (
                  <tr key={schedule.id}>
                    <td>{schedule.instructor_name}</td>
                    <td>{schedule.level_name}</td>
                    <td>{schedule.skill_name}</td>
                    <td>{new Date(schedule.target_date + "T00:00:00").toLocaleDateString()}</td>
                    <td>{schedule.status}</td>
                    <td>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        <button type="button" onClick={() => void updateScheduleStatus(schedule, "IN_PROGRESS")}>Start</button>
                        <button type="button" onClick={() => handleCompleteScheduled(schedule)}>Complete</button>
                        <button type="button" className="btn-add" onClick={() => startEditSchedule(schedule)}>Edit</button>
                        <button type="button" className="btn-add" onClick={() => void updateScheduleStatus(schedule, "CANCELED")}>Cancel</button>
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

        <div style={{ marginTop: 8 }}>
          {showCreate && (
            <SupervisorCreateEvaluation
              token={token}
              users={users}
              levels={levels}
              skills={skills}
              prefill={selectedReeval}
              assignedEvals={activeScheduled}
              onSelectAssignedEval={handleCompleteScheduled}
              onCreated={(created) => {
                handleCreated(created);
                setSelectedReeval(null);
                setShowCreate(false);
              }}
              onCancel={() => {
                setSelectedReeval(null);
                setShowCreate(false);
              }}
            />
          )}
        </div>
      </div>

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ marginBottom: 0 }}>Evaluation Management</h2>
        </div>
        <p style={{ color: "#64748b", fontSize: 14, lineHeight: 1.6 }}>
          Use this view to create new evaluations and respond to open reevaluation requests.
          For the full evaluation history, filters, and modal-based view/edit actions, use the
          Evaluations page.
        </p>
        <div
          style={{
            marginTop: 14,
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: 12,
            alignItems: "end",
          }}
        >
          <label style={{ margin: 0 }}>
            Instructor
            <select
              value={filters.instructorId}
              onChange={(e) => setFilters((prev) => ({ ...prev, instructorId: e.target.value }))}
            >
              <option value="">All instructors</option>
              {users.map((userItem) => (
                <option key={userItem.id} value={userItem.id}>
                  {userItem.full_name}
                </option>
              ))}
            </select>
          </label>
          <label style={{ margin: 0 }}>
            Skill
            <select
              value={filters.skillId}
              onChange={(e) => setFilters((prev) => ({ ...prev, skillId: e.target.value }))}
            >
              <option value="">All skills</option>
              {skills.map((skill) => (
                <option key={skill.id} value={skill.id}>
                  {skill.name}
                </option>
              ))}
            </select>
          </label>
          <label style={{ margin: 0 }}>
            Status
            <select
              value={filters.needsReevaluation}
              onChange={(e) => setFilters((prev) => ({ ...prev, needsReevaluation: e.target.value }))}
            >
              <option value="">All statuses</option>
              <option value="true">Needs Reevaluation</option>
              <option value="false">No Reevaluation Needed</option>
            </select>
          </label>
        </div>
      </div>

      <SupervisorReevaluationPanel
        users={users}
        skills={skills}
        assignedEvaluations={filteredAssignedEvaluations}
        filters={filters}
        setFilters={setFilters}
        onReevaluate={handleAssignedReevaluation}
      />
    </>
  );
}
