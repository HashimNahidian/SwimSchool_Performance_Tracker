import { FormEvent, useState } from "react";
import { updateSupervisorEvaluation, submitSupervisorEvaluation } from "../api";
import type { EvaluationDetail } from "../types";

const RATING_LABEL: Record<number, string> = {
  1: "1 — Remediate",
  2: "2 — Meets Standard",
  3: "3 — Exceeds Standard",
};

export function EvaluationEditModal({
  token,
  evaluation,
  onSaved,
  onSubmitted,
  onClose,
}: {
  token: string;
  evaluation: EvaluationDetail;
  onSaved: (updated: EvaluationDetail) => void;
  onSubmitted: (updated: EvaluationDetail) => void;
  onClose: () => void;
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
      const updated = await updateSupervisorEvaluation(token, evaluation.id, {
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
      // Save latest edits first, then submit
      await updateSupervisorEvaluation(token, evaluation.id, {
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
            Edit Draft — #{evaluation.id} &nbsp;·&nbsp; {evaluation.instructor_name}
          </span>
          <button className="btn-add" onClick={onClose}>✕ Close</button>
        </div>

        {/* Info row */}
        <div className="report-info-grid" style={{ marginBottom: 16 }}>
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
          {/* Ratings */}
          <fieldset style={{ padding: 14, borderRadius: 10, border: "1px solid #bbd6ea" }}>
            <legend style={{ fontWeight: 700, color: "#023e8a", padding: "0 6px" }}>
              Performance Ratings
            </legend>
            <p style={{ fontSize: 13, color: "#64748b", marginBottom: 12 }}>
              Adjust ratings for each criterion below.
            </p>
            {evaluation.ratings.map((r) => (
              <label key={r.attribute_id} className="inline-rating">
                <span style={{ minWidth: 180 }}>{r.attribute_name}</span>
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
            ))}
          </fieldset>

          {/* Notes */}
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

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button type="submit" disabled={saving}>
              {saving ? "Saving..." : "💾 Save Draft"}
            </button>

            {!confirmSubmit ? (
              <button
                type="button"
                style={{ background: "#0f9b8e" }}
                onClick={() => setConfirmSubmit(true)}
              >
                ✅ Submit Evaluation
              </button>
            ) : (
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
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
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
