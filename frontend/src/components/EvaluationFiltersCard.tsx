import { useMemo, useState } from "react";
import type { Dispatch, ReactNode, SetStateAction } from "react";
import type { Skill, User } from "../types";

const DAY_OPTIONS = [
  { value: 1, label: "Mon", longLabel: "Monday" },
  { value: 2, label: "Tue", longLabel: "Tuesday" },
  { value: 3, label: "Wed", longLabel: "Wednesday" },
  { value: 4, label: "Thu", longLabel: "Thursday" },
  { value: 5, label: "Fri", longLabel: "Friday" },
  { value: 6, label: "Sat", longLabel: "Saturday" },
  { value: 0, label: "Sun", longLabel: "Sunday" },
];

const SORT_OPTIONS = [
  { value: "created_at:desc", label: "Created At (Newest first)" },
  { value: "created_at:asc", label: "Created At (Oldest first)" },
  { value: "updated_at:desc", label: "Updated At (Newest first)" },
  { value: "updated_at:asc", label: "Updated At (Oldest first)" },
  { value: "final_grade:desc", label: "Final Grade (High to Low)" },
  { value: "final_grade:asc", label: "Final Grade (Low to High)" },
  { value: "id:desc", label: "ID (Highest first)" },
  { value: "id:asc", label: "ID (Lowest first)" },
  { value: "instructor_id:asc", label: "Instructor (A to Z)" },
  { value: "instructor_id:desc", label: "Instructor (Z to A)" },
  { value: "supervisor_id:asc", label: "Supervisor (A to Z)", managerOnly: true },
  { value: "supervisor_id:desc", label: "Supervisor (Z to A)", managerOnly: true },
];

export type EvaluationFilterValues = {
  instructor_id: string;
  supervisor_id: string;
  skill_id: string;
  final_grade: string;
  needs_reevaluation: string;
  date_from: string;
  date_to: string;
  sort_option: string;
  selected_days: number[];
};

function activeFilterChips(
  filters: EvaluationFilterValues,
  instructors: User[],
  supervisors: User[],
  skills: Skill[],
) {
  const chips: Array<{ key: string; label: string; clear: (setFilters: Dispatch<SetStateAction<EvaluationFilterValues>>) => void }> = [];

  if (filters.instructor_id) {
    const instructor = instructors.find((user) => String(user.id) === filters.instructor_id);
    if (instructor) {
      chips.push({
        key: "instructor_id",
        label: `Instructor: ${instructor.full_name}`,
        clear: (setFilters) => setFilters((prev) => ({ ...prev, instructor_id: "" })),
      });
    }
  }

  if (filters.supervisor_id) {
    const supervisor = supervisors.find((user) => String(user.id) === filters.supervisor_id);
    if (supervisor) {
      chips.push({
        key: "supervisor_id",
        label: `Supervisor: ${supervisor.full_name}`,
        clear: (setFilters) => setFilters((prev) => ({ ...prev, supervisor_id: "" })),
      });
    }
  }

  if (filters.skill_id) {
    const skill = skills.find((item) => String(item.id) === filters.skill_id);
    if (skill) {
      chips.push({
        key: "skill_id",
        label: `Skill: ${skill.name}`,
        clear: (setFilters) => setFilters((prev) => ({ ...prev, skill_id: "" })),
      });
    }
  }

  if (filters.final_grade) {
    chips.push({
      key: "final_grade",
      label: `Grade: ${filters.final_grade}`,
      clear: (setFilters) => setFilters((prev) => ({ ...prev, final_grade: "" })),
    });
  }

  if (filters.needs_reevaluation) {
    chips.push({
      key: "needs_reevaluation",
      label: filters.needs_reevaluation === "true" ? "Needs Reevaluation" : "No Reevaluation Needed",
      clear: (setFilters) => setFilters((prev) => ({ ...prev, needs_reevaluation: "" })),
    });
  }

  if (filters.selected_days.length > 0) {
    chips.push({
      key: "selected_days",
      label: `Days: ${DAY_OPTIONS.filter((day) => filters.selected_days.includes(day.value)).map((day) => day.label).join(", ")}`,
      clear: (setFilters) => setFilters((prev) => ({ ...prev, selected_days: [] })),
    });
  }

  if (filters.date_from || filters.date_to) {
    chips.push({
      key: "date_range",
      label: `Date: ${filters.date_from || "Any"} to ${filters.date_to || "Any"}`,
      clear: (setFilters) => setFilters((prev) => ({ ...prev, date_from: "", date_to: "" })),
    });
  }

  if (filters.sort_option !== "created_at:desc") {
    const sort = SORT_OPTIONS.find((option) => option.value === filters.sort_option);
    if (sort) {
      chips.push({
        key: "sort_option",
        label: `Sort: ${sort.label}`,
        clear: (setFilters) => setFilters((prev) => ({ ...prev, sort_option: "created_at:desc" })),
      });
    }
  }

  return chips;
}

export function EvaluationFiltersCard({
  title = "Filters",
  filters,
  setFilters,
  skills,
  instructors,
  supervisors,
  showSupervisorFilter = false,
  onApply,
  onClear,
  actions,
}: {
  title?: string;
  filters: EvaluationFilterValues;
  setFilters: Dispatch<SetStateAction<EvaluationFilterValues>>;
  skills: Skill[];
  instructors: User[];
  supervisors?: User[];
  showSupervisorFilter?: boolean;
  onApply: () => void;
  onClear?: () => void;
  actions?: ReactNode;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const availableSortOptions = useMemo(
    () => SORT_OPTIONS.filter((option) => showSupervisorFilter || !option.managerOnly),
    [showSupervisorFilter],
  );
  const chips = useMemo(
    () => activeFilterChips(filters, instructors, supervisors ?? [], skills),
    [filters, instructors, supervisors, skills],
  );

  function toggleDay(day: number) {
    setFilters((prev) => ({
      ...prev,
      selected_days: prev.selected_days.includes(day)
        ? prev.selected_days.filter((value) => value !== day)
        : [...prev.selected_days, day],
    }));
  }

  return (
    <div className="card evaluation-sidebar-card">
      <div className="evaluation-sidebar-header">
        <div>
          <h2 style={{ marginBottom: 0 }}>{title}</h2>
          <p className="evaluation-sidebar-subtitle">Refine the evaluation results shown on the right.</p>
        </div>
        <button
          type="button"
          className="btn-add evaluation-sidebar-toggle"
          onClick={() => setMobileOpen((prev) => !prev)}
          aria-expanded={mobileOpen}
        >
          {mobileOpen ? "Hide Filters" : "Show Filters"}
        </button>
      </div>

      {(actions || chips.length > 0) && (
        <div className="evaluation-sidebar-top">
          {actions && <div className="evaluation-sidebar-actions">{actions}</div>}
          {chips.length > 0 && (
            <div className="evaluation-active-filters">
              <div className="evaluation-section-heading-row">
                <p className="evaluation-section-title">Active Filters</p>
                {onClear && (
                  <button type="button" className="evaluation-text-action" onClick={onClear}>
                    Clear all
                  </button>
                )}
              </div>
              <div className="evaluation-chip-list">
                {chips.map((chip) => (
                  <button
                    key={chip.key}
                    type="button"
                    className="evaluation-chip"
                    onClick={() => chip.clear(setFilters)}
                    aria-label={`Remove filter ${chip.label}`}
                  >
                    <span>{chip.label}</span>
                    <span aria-hidden="true">×</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <form
        className={`evaluation-sidebar-form${mobileOpen ? " open" : ""}`}
        onSubmit={(e) => {
          e.preventDefault();
          onApply();
        }}
      >
        <section className="evaluation-filter-section">
          <div className="evaluation-section-heading-row">
            <p className="evaluation-section-title">People</p>
          </div>
          <label className="evaluation-filter-group">
            <span className="evaluation-filter-label">Instructor</span>
            <select
              value={filters.instructor_id}
              onChange={(e) => setFilters((prev) => ({ ...prev, instructor_id: e.target.value }))}
            >
              <option value="">All instructors</option>
              {instructors.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.full_name}
                </option>
              ))}
            </select>
          </label>

          {showSupervisorFilter && (
            <label className="evaluation-filter-group">
              <span className="evaluation-filter-label">Supervisor</span>
              <select
                value={filters.supervisor_id}
                onChange={(e) => setFilters((prev) => ({ ...prev, supervisor_id: e.target.value }))}
              >
                <option value="">All supervisors</option>
                {supervisors?.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.full_name}
                  </option>
                ))}
              </select>
            </label>
          )}

          <label className="evaluation-filter-group">
            <span className="evaluation-filter-label">Skill</span>
            <select
              value={filters.skill_id}
              onChange={(e) => setFilters((prev) => ({ ...prev, skill_id: e.target.value }))}
            >
              <option value="">All skills</option>
              {skills.map((skill) => (
                <option key={skill.id} value={skill.id}>
                  {skill.name}
                </option>
              ))}
            </select>
          </label>
        </section>

        <section className="evaluation-filter-section">
          <div className="evaluation-section-heading-row">
            <p className="evaluation-section-title">Status</p>
          </div>
          <label className="evaluation-filter-group">
            <span className="evaluation-filter-label">Final Grade</span>
            <select
              value={filters.final_grade}
              onChange={(e) => setFilters((prev) => ({ ...prev, final_grade: e.target.value }))}
            >
              <option value="">All grades</option>
              <option value="1">1 — Does not meet Standards</option>
              <option value="2">2 — Needs Improvement</option>
              <option value="3">3 — Meets Standard</option>
              <option value="4">4 — Exceeds Standard</option>
              <option value="5">5 — Outstanding</option>
            </select>
          </label>

          <div className="evaluation-filter-group">
            <span className="evaluation-filter-label">Needs Reevaluation</span>
            <div className="evaluation-segmented" role="radiogroup" aria-label="Needs reevaluation">
              {[
                { value: "", label: "All" },
                { value: "true", label: "Needs Reevaluation" },
                { value: "false", label: "Does Not Need Reevaluation" },
              ].map((option) => (
                <button
                  key={option.value || "all"}
                  type="button"
                  className={`evaluation-segment${filters.needs_reevaluation === option.value ? " active" : ""}`}
                  onClick={() => setFilters((prev) => ({ ...prev, needs_reevaluation: option.value }))}
                  aria-pressed={filters.needs_reevaluation === option.value}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        </section>

        <section className="evaluation-filter-section">
          <div className="evaluation-section-heading-row">
            <p className="evaluation-section-title">Time</p>
          </div>
          <div className="evaluation-filter-group">
            <span className="evaluation-filter-label">Day of Week</span>
            <div className="evaluation-day-chips" role="group" aria-label="Day of week">
              {DAY_OPTIONS.map((day) => (
                <button
                  key={day.value}
                  type="button"
                  className={`evaluation-day-chip${filters.selected_days.includes(day.value) ? " active" : ""}`}
                  onClick={() => toggleDay(day.value)}
                  aria-pressed={filters.selected_days.includes(day.value)}
                >
                  {day.label}
                </button>
              ))}
            </div>
          </div>

          <div className="evaluation-filter-group">
            <span className="evaluation-filter-label">Date Range</span>
            <div className="evaluation-date-range paired">
              <label className="evaluation-inline-field">
                <span className="evaluation-inline-label">Start date</span>
                <input
                  type="date"
                  value={filters.date_from}
                  onChange={(e) => setFilters((prev) => ({ ...prev, date_from: e.target.value }))}
                />
              </label>
              <label className="evaluation-inline-field">
                <span className="evaluation-inline-label">End date</span>
                <input
                  type="date"
                  value={filters.date_to}
                  onChange={(e) => setFilters((prev) => ({ ...prev, date_to: e.target.value }))}
                />
              </label>
            </div>
          </div>
        </section>

        <section className="evaluation-filter-section">
          <div className="evaluation-section-heading-row">
            <p className="evaluation-section-title">Sorting</p>
          </div>
          <label className="evaluation-filter-group">
            <span className="evaluation-filter-label">Sort By</span>
            <select
              value={filters.sort_option}
              onChange={(e) => setFilters((prev) => ({ ...prev, sort_option: e.target.value }))}
            >
              {availableSortOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </section>

        <div className="evaluation-sidebar-button-row">
          <button type="submit">Apply Filters</button>
          {onClear && (
            <button type="button" className="btn-add evaluation-secondary-button" onClick={onClear}>
              Clear Filters
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
