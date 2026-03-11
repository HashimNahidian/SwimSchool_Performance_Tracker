import { FormEvent, useState } from "react";
import { submitSupervisorEvaluation, updateSupervisorEvaluation } from "../api";
import type { EvaluationDetail } from "../types";

const RATING_LABEL: Record<number, string> = {
  1: "1 - Remediate",
  2: "2 - Meets Standard",
  3: "3 - Exceeds Standard",
};

export function EvaluationEditModal({
  token,
  evaluation,
  onSaved,
  onSubmitted,
  onClose,
  updateFn = updateSupervisorEvaluation,
  showSubmit = true,
}: {
  token: string;
  evaluation: EvaluationDetail;
  onSaved: (updated: EvaluationDetail) => void;
  onSubmitted: (updated: EvaluationDetail) => void;
  onClose: () => void;
  updateFn?: (token: string, id: number, payload: { notes?: string | null; ratings?: Array<{ attribute_id: number; rating_value: number }> }) => Promise<EvaluationDetail>;
  showSubmit?: boolean;
}) {
  const [notes, setNotes] = useState(evaluation.notes ?? "");
  const [ratings, setRatings] = useState<Record<number, number>>(
    Object.fromEntries(evaluation.ratings.map((r) => [r.attribute_id, r.rating_value]))
  );
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [confirmSubmit, setConfirmSubmit] = useState(false);

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const updated = await updateFn(token, evaluation.id, {
        notes: notes.trim() || null,
        ratings: Object.entries(ratings).map(([id, value]) => ({
          attribute_id: Number(id),
          rating_value: value,
        })),
      });
      onSaved(updated);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmit() {
    setSubmitting(true);
    setError("");
    try {
      await updateFn(token, evaluation.id, {
        notes: notes.trim() || null,
        ratings: Object.entries(ratings).map(([id, value]) => ({
          attribute_id: Number(id),
          rating_value: value,
        })),
      });
      const submitted = await submitSupervisorEvaluation(token, evaluation.id);
      onSubmitted(submitted);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
      setConfirmSubmit(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-toolbar">
          <span style={{ fontWeight: 700, color: "#023e8a", fontSize: 15 }}>
            Edit Draft - #{evaluation.id} - {evaluation.instructor_name}
          </span>
          <button className="btn-add" onClick={onClose}>Close</button>
        </div>

        <div className="edit-modal-body">
          <div className="report-info-grid edit-modal-info-grid">
            <div className="report-info-item">
              <span className="report-info-label">Level</span>
              <span className="report-info-value">{evaluation.level_name}</span>
            </div>
            <div className="report-info-item">
              <span className="report-info-label">Skill</span>
              <span className="report-info-value">{evaluation.skill_name}</span>
            </div>
            <div className="report-info-item">
              <span className="report-info-label">Session</span>
              <span className="report-info-value">{evaluation.session_label}</span>
            </div>
            <div className="report-info-item">
              <span className="report-info-label">Date</span>
              <span className="report-info-value">{evaluation.session_date}</span>
            </div>
          </div>

          <form className="form" onSubmit={handleSave}>
            <fieldset className="edit-ratings-fieldset">
              <legend style={{ fontWeight: 700, color: "#023e8a", padding: "0 6px" }}>
                Performance Ratings
              </legend>
              <p style={{ fontSize: 13, color: "#64748b", marginBottom: 12 }}>
                Adjust ratings for each criterion below.
              </p>
              {evaluation.ratings.length > 0 ? (
                evaluation.ratings.map((r) => (
                  <label key={r.attribute_id} className="inline-rating edit-rating-row">
                    <span className="edit-rating-label">{r.attribute_name}</span>
                    <select
                      value={ratings[r.attribute_id] ?? 2}
                      onChange={(e) =>
                        setRatings((prev) => ({ ...prev, [r.attribute_id]: Number(e.target.value) }))
                      }
                    >
                      {[1, 2, 3].map((v) => (
                        <option key={v} value={v}>{RATING_LABEL[v]}</option>
                      ))}
                    </select>
                  </label>
                ))
              ) : (
                <div className="edit-ratings-empty">
                  No rating criteria available for this evaluation yet.
                </div>
              )}
            </fieldset>

            <label>
              Supervisor Notes
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={4}
                placeholder="Optional coaching notes..."
              />
            </label>

            {error && <p className="error">{error}</p>}

            <div className="edit-modal-actions">
              <button type="submit" disabled={saving}>
                {saving ? "Saving..." : "Save Changes"}
              </button>

              {showSubmit && (
                !confirmSubmit ? (
                  <button
                    type="button"
                    style={{ background: "#0f9b8e" }}
                    onClick={() => setConfirmSubmit(true)}
                  >
                    Submit Evaluation
                  </button>
                ) : (
                  <div className="edit-modal-confirm-row">
                    <span style={{ fontSize: 14, fontWeight: 600, color: "#023e8a" }}>
                      Submit and lock this evaluation?
                    </span>
                    <button
                      type="button"
                      style={{ background: "#0f9b8e" }}
                      disabled={submitting}
                      onClick={handleSubmit}
                    >
                      {submitting ? "Submitting..." : "Confirm Submit"}
                    </button>
                    <button
                      type="button"
                      className="btn-add"
                      onClick={() => setConfirmSubmit(false)}
                    >
                      Cancel
                    </button>
                  </div>
                )
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
