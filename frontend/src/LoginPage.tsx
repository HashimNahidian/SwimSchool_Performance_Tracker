import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "./auth";

export function LoginPage() {
  const { login, user } = useAuth();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (user) {
    return <Navigate to={`/${user.role.toLowerCase()}`} replace />;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel narrow">
      <h2>Login</h2>
      <p>Use an existing user email from the backend.</p>
      <form onSubmit={onSubmit} className="stack">
        <label>
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="manager@propel.local"
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Signing in..." : "Sign in"}
        </button>
        {error && <p className="error">{error}</p>}
      </form>
    </section>
  );
}
