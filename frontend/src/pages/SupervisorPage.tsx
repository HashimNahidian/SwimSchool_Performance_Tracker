import { useState } from "react";
import { SupervisorCreateEvaluation, SupervisorReevaluationPanel, useSupervisorData } from "./supervisor/shared";

export function SupervisorPage() {
  const {
    token,
    user,
    error,
    users,
    levels,
    skills,
    filteredReevaluations,
    filters,
    setFilters,
    stats,
    handleCompleteReevaluation,
    handleCreated,
  } = useSupervisorData();
  const [showCreate, setShowCreate] = useState(false);

  if (!token) return null;

  return (
    <>
      {error && <p className="error">{error}</p>}

      <div className="page-heading">
        <h1 className="page-title">Welcome back, {user?.full_name ?? "Supervisor"}</h1>
        <p className="page-subtitle">Create new evaluations and work through reevaluation requests.</p>
      </div>

      <div className="stat-cards supervisor-stat-cards">
        <div className="stat-card">
          <div className="stat-card-value" style={{ color: "#023e8a" }}>{stats.total}</div>
          <div className="stat-card-label">Total Evaluations this month</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-value" style={{ color: "#0f9b8e" }}>{stats.instructorCount}</div>
          <div className="stat-card-label">Instructors evaluated this month</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-value" style={{ color: "#c2550a" }}>{stats.flaggedCount}</div>
          <div className="stat-card-label">Assigned Evaluations</div>
        </div>
      </div>

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ marginBottom: 0 }}>Evaluation Management</h2>
          <button
            className="btn-add"
            onClick={() => setShowCreate((prev) => !prev)}
          >
            {showCreate ? "Cancel" : "+ New Evaluation"}
          </button>
        </div>
        <p style={{ color: "#64748b", fontSize: 14, lineHeight: 1.6 }}>
          Use this view to create new evaluations and respond to open reevaluation requests.
          For the full evaluation history, filters, and modal-based view/edit actions, use the
          Evaluations page.
        </p>
        <div style={{ marginTop: 14, display: "flex", flexWrap: "wrap", gap: 8 }}>
          {users.map((userItem) => (
            <span
              key={userItem.id}
              style={{
                padding: "6px 10px",
                borderRadius: 999,
                background: "#eff6ff",
                color: "#0f3d68",
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              {userItem.full_name}
            </span>
          ))}
        </div>
      </div>

      {showCreate && (
        <SupervisorCreateEvaluation
          token={token}
          users={users}
          levels={levels}
          skills={skills}
          prefill={null}
          onCreated={(created) => {
            handleCreated(created);
            setShowCreate(false);
          }}
          onCancel={() => setShowCreate(false)}
        />
      )}

      <SupervisorReevaluationPanel
        users={users}
        skills={skills}
        filteredReevaluations={filteredReevaluations}
        filters={filters}
        setFilters={setFilters}
        onComplete={handleCompleteReevaluation}
      />
    </>
  );
}
