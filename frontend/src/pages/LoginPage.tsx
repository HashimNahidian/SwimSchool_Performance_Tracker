import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { WaveLogo } from "../components/WaveLogo";

export function LoginPage() {
  const { login, user } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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
      await login(email, password);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-bg">
      <div className="login-card">
        <div className="login-logo">
          <WaveLogo size={80} light />
          <h1 className="login-brand">PROPEL SWIM SCHOOL</h1>
          <p className="login-subtitle">Instructor Evaluation Portal</p>
        </div>

        <form onSubmit={onSubmit} className="login-form">
          <label className="login-label">
            Email
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="instructor@propelswim.com"
              className="login-input"
            />
          </label>
          <label className="login-label">
            Password
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="login-input"
            />
          </label>
          {error && <p className="error">{error}</p>}
          <button type="submit" className="dive-in-btn" disabled={loading}>
            {loading ? "Signing in..." : "Dive In ✦"}
          </button>
        </form>

        <p className="trouble-login">Trouble Logging In?</p>
      </div>
    </div>
  );
}
