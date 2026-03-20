import { EvaluationEditModal } from "../components/EvaluationEditModal";
import { EvaluationReportModal } from "../components/EvaluationReport";
import { EvaluationTable } from "../components/EvaluationTable";
import { EvaluationFiltersCard, type EvaluationFilterValues } from "../components/EvaluationFiltersCard";
import { EvaluationMonthlyStats } from "../components/EvaluationMonthlyStats";
import { SupervisorCreateEvaluation, SupervisorReevaluationPanel, ReevaluationPrefill, useSupervisorData } from "./supervisor/shared";
import { useState } from "react";

export function SupervisorEvaluationsPage() {
  const {
    token,
    user,
    error,
    users,
    levels,
    skills,
    reportEval,
    setReportEval,
    editEval,
    setEditEval,
    loadingDetail,
    needsReevalMode,
    setNeedsReevalMode,
    filters,
    setFilters,
    applyFilters,
    clearFilters,
    filteredRows,
    filteredAssignedEvaluations,
    openDetail,
    handleSaved,
    handleCreated,
  } = useSupervisorData();
  const [showCreateInput, setShowCreateInput] = useState(false);
  const [selectedReeval, setSelectedReeval] = useState<ReevaluationPrefill | null>(null);

  if (!token) return null;

  function handleReevaluate(evaluationId: number) {
    const row = filteredRows.find((item) => item.id === evaluationId);
    if (!row) return;
    setSelectedReeval({
      evaluationId: row.id,
      instructorId: row.instructor_id,
      levelId: row.level_id,
      skillId: row.skill_id,
      sourceEvalId: row.id,
      mode: "reevaluation",
    });
    setShowCreateInput(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <>
      {error && <p className="error">{error}</p>}

      <div className="page-heading">
        <h1 className="page-title">Welcome back, {user?.full_name ?? "Supervisor"}</h1>
        <p className="page-subtitle">Review evaluation history, filter results, and open reports without leaving the page.</p>
      </div>

      <EvaluationMonthlyStats
        rows={filteredRows}
        flaggedLabel="Assigned Evaluations"
        flaggedActive={needsReevalMode}
        onFlaggedClick={() => setNeedsReevalMode((prev) => !prev)}
      />

      {showCreateInput && selectedReeval && (
        <SupervisorCreateEvaluation
          token={token}
          users={users}
          levels={levels}
          skills={skills}
          prefill={selectedReeval}
          onCreated={(created) => {
            handleCreated(created);
            setSelectedReeval(null);
            setShowCreateInput(false);
          }}
          onCancel={() => {
            setSelectedReeval(null);
            setShowCreateInput(false);
          }}
        />
      )}

      <div className="evaluation-layout">
        <aside className="evaluation-sidebar">
          <EvaluationFiltersCard
            title="Filter Evaluations"
            filters={{
              instructor_id: filters.instructorId,
              supervisor_id: "",
              skill_id: filters.skillId,
              final_grade: filters.finalGrade,
              needs_reevaluation: filters.needsReevaluation,
              date_from: filters.dateFrom,
              date_to: filters.dateTo,
              sort_option: filters.sortOption,
              selected_days: filters.selectedDays,
            }}
            setFilters={(updater) => {
              setFilters((prev) => {
                const next = typeof updater === "function"
                  ? updater({
                      instructor_id: prev.instructorId,
                      supervisor_id: prev.supervisorId,
                      skill_id: prev.skillId,
                      final_grade: prev.finalGrade,
                      needs_reevaluation: prev.needsReevaluation,
                      date_from: prev.dateFrom,
                      date_to: prev.dateTo,
                      sort_option: prev.sortOption,
                      selected_days: prev.selectedDays,
                    } as EvaluationFilterValues)
                  : updater;
                return {
                  ...prev,
                  instructorId: next.instructor_id,
                  supervisorId: next.supervisor_id,
                  skillId: next.skill_id,
                  finalGrade: next.final_grade,
                  needsReevaluation: next.needs_reevaluation,
                  dateFrom: next.date_from,
                  dateTo: next.date_to,
                  sortOption: next.sort_option,
                  selectedDays: next.selected_days,
                };
              });
            }}
            skills={skills}
            instructors={users}
            onApply={applyFilters}
            onClear={clearFilters}
          />
        </aside>

        <div className="evaluation-main">
          <SupervisorReevaluationPanel
            users={users}
            skills={skills}
            assignedEvaluations={filteredAssignedEvaluations}
            filters={filters}
            setFilters={setFilters}
            onReevaluate={(evaluation) => handleReevaluate(evaluation.id)}
            showControls={false}
          />

          <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ marginBottom: 0 }}>
            Evaluations
            {loadingDetail && <span style={{ fontSize: 13, color: "#64748b", fontWeight: 400, marginLeft: 8 }}>Loading...</span>}
          </h2>
        </div>

        {needsReevalMode && (
          <p style={{ marginTop: -4, marginBottom: 14, color: "#c2550a", fontWeight: 600 }}>
            Showing only evaluations that need reevaluation.
          </p>
        )}

        <EvaluationTable
          rows={filteredRows}
          onView={(id) => openDetail(id, "view")}
          onEdit={(id) => openDetail(id, "edit")}
          onReevaluate={handleReevaluate}
        />
        {filteredRows.length === 0 && (
          <p style={{ color: "#64748b", fontSize: 14, paddingTop: 8 }}>No evaluations match the current filters.</p>
        )}
      </div>
        </div>
      </div>

      {reportEval && <EvaluationReportModal evaluation={reportEval} onClose={() => setReportEval(null)} />}

      {editEval && (
        <EvaluationEditModal
          token={token}
          evaluation={editEval}
          onSaved={handleSaved}
          onSubmitted={handleSaved}
          onClose={() => setEditEval(null)}
        />
      )}
    </>
  );
}
