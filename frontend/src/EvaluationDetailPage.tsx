import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiRequest } from "./api";
import { useAuth } from "./auth";
import type { Attribute, Evaluation } from "./types";

export function EvaluationDetailPage() {
  const { token } = useAuth();
  const { evaluationId } = useParams();
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [attributes, setAttributes] = useState<Attribute[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function run() {
      if (!token || !evaluationId) return;
      try {
        const [evaluationData, attributesData] = await Promise.all([
          apiRequest<Evaluation>(`/evaluations/${evaluationId}`, {}, token),
          apiRequest<Attribute[]>("/attributes", {}, token)
        ]);
        setEvaluation(evaluationData);
        setAttributes(attributesData);
      } catch (err) {
        setError((err as Error).message);
      }
    }
    void run();
  }, [token, evaluationId]);

  const attributeMap = new Map(attributes.map((attribute) => [attribute.id, attribute.name]));

  if (error) return <p className="error">{error}</p>;
  if (!evaluation) return <p>Loading...</p>;

  return (
    <section className="panel">
      <h2>Evaluation #{evaluation.id}</h2>
      <p>Date: {evaluation.session_date}</p>
      <p>Status: {evaluation.status}</p>
      <p>Session: {evaluation.session_label || "N/A"}</p>
      <p>Notes: {evaluation.notes || "N/A"}</p>
      <h3>Ratings</h3>
      <ul>
        {evaluation.ratings.map((rating) => (
          <li key={rating.attribute_id}>
            {attributeMap.get(rating.attribute_id) || `Attribute ${rating.attribute_id}`}: {rating.rating_value}
          </li>
        ))}
      </ul>
    </section>
  );
}
