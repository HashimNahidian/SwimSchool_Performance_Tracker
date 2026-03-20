import { FormEvent, useState } from "react";
import { updateSupervisorEvaluation } from "../api";
import { EvaluationTimer } from "./EvaluationTimer";
import type { EvaluationDetail } from "../types";

const RATING_LABEL: Record<number, string> = {
  1: "1 - Does not meet Standards",
  2: "2 - Needs Improvement",
  3: "3 - Meets Standard",
  4: "4 - Exceeds Standard",
  5: "5 - Outstanding",
};

export function EvaluationEditModal({
  token,
  evaluation,
  onSaved,
  onSubmitted,
  onClose,
  updateFn = updateSupervisorEvaluation,
  showSubmit = false,
}: {
  token: string;
  evaluation: EvaluationDetail;
  onSaved: (updated: EvaluationDetail) => void;
  onSubmitted: (updated: EvaluationDetail) => void;
  onClose: () => void;
  updateFn?: (
    token: string,
    id: number,
    payload: {
      notes?: string | null;
      duration_seconds?: number | null;
      ratings?: Array<{ attribute_id: number; rating: number; comment?: string | null }>;
      needs_reevaluation?: boolean;
    }
  ) => Promise<EvaluationDetail>;
  showSubmit?: boolean;
}) {
  const [notes, setNotes] = useState(evaluation.notes ?? "");
  const [durationSeconds, setDurationSeconds] = useState<number | null>(evaluation.duration_seconds ?? null);
  const [needsReevaluation, setNeedsReevaluation] = useState(evaluation.needs_reevaluation);
  const [ratings, setRatings] = useState<Record<number, number>>(
    Object.fromEntries(evaluation.ratings.map((r) => [r.attribute_id, r.rating]))
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const updated = await updateFn(token, evaluation.id, {
        notes: notes.trim() || null,
        duration_seconds: durationSeconds,
        ratings: Object.entries(ratings).map(([id, value]) => ({
          attribute_id: Number(id),
          rating: value,
        })),
        needs_reevaluation: needsReevaluation,
      });
      onSaved(updated);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-toolbar">
          <span style={{ fontWeight: 700, color: "#023e8a", fontSize: 15 }}>
            Edit Evaluation - #{evaluation.id} - {evaluation.instructor_name}
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
              <span className="report-info-label">Date</span>
              <span className="report-info-value">{new Date(evaluation.created_at).toLocaleDateString()}</span>
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
                      value={ratings[r.attribute_id] ?? 3}
                      onChange={(e) =>
                        setRatings((prev) => ({ ...prev, [r.attribute_id]: Number(e.target.value) }))
                      }
                    >
                      {[1, 2, 3, 4, 5].map((v) => (
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

            <div>
              <div style={{ fontWeight: 700, color: "#023e8a", marginBottom: 8 }}>Skill time tracking</div>
              <EvaluationTimer
                initialSeconds={evaluation.duration_seconds ?? 0}
                onChange={(seconds) => setDurationSeconds(seconds)}
              />
            </div>

            <label style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 600 }}>
              <input
                type="checkbox"
                checked={needsReevaluation}
                onChange={(e) => setNeedsReevaluation(e.target.checked)}
                style={{ width: "auto" }}
              />
              Mark as needing reevaluation
            </label>

            {error && <p className="error">{error}</p>}

            <div className="edit-modal-actions">
              <button type="submit" disabled={saving}>
                {saving ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
