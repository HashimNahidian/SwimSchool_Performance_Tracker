import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../auth";
import { WaveLogo } from "../components/WaveLogo";

export function LoginPage() {
  const { login, user } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  if (user) {
    return <Navigate to={`/${user.role.toLowerCase()}`} replace />;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(username, password);
    } catch {
      setError("Invalid username or password");
    } finally {
      setLoading(false);
    }
  }

  const hasError = Boolean(error);

  return (
    <div className="login-bg">
      <div className="login-card">
        <div className="login-logo">
          <WaveLogo size={80} light />
          <h1 className="login-brand">PROPEL SWIM ACADEMY</h1>
          <p className="login-subtitle">Evaluation Portal</p>
        </div>

        <form onSubmit={onSubmit} className="login-form">
          <label className="login-label">
            Username
            <input
              type="text"
              required
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                if (error) setError(null);
              }}
              placeholder="Enter username or email"
              className={`login-input ${hasError ? "login-input-error login-input-shake" : ""}`}
              autoComplete="username"
              aria-invalid={hasError}
              aria-describedby={hasError ? "login-error-message" : undefined}
            />
          </label>
          <label className="login-label login-password-label">
            Password
            <span className="login-password-wrap">
              <input
                type={showPassword ? "text" : "password"}
                required
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (error) setError(null);
                }}
                placeholder="••••••••"
                className={`login-input login-password-input ${hasError ? "login-input-error login-input-shake" : ""}`}
                autoComplete="current-password"
                aria-invalid={hasError}
                aria-describedby={hasError ? "login-error-message" : undefined}
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword((current) => !current)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
              >
                <span className="password-toggle-icon" aria-hidden="true">
                  {showPassword ? (
                    <svg viewBox="0 0 24 24" focusable="false">
                      <path d="M3 5.5 19 21.5" />
                      <path d="M10.58 10.58A2 2 0 0 0 12 14a2 2 0 0 0 1.42-.58" />
                      <path d="M9.88 5.09A10.94 10.94 0 0 1 12 4.9c5.3 0 9.27 4.2 10 6.1a11.8 11.8 0 0 1-3.2 4.23" />
                      <path d="M6.61 6.62A12.08 12.08 0 0 0 2 11c.54 1.36 2.69 4.64 6.79 5.74" />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 24 24" focusable="false">
                      <path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12Z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </span>
              </button>
            </span>
          </label>
          {error && (
            <p id="login-error-message" className="login-error" role="alert" aria-live="polite">
              {error}
            </p>
          )}
          <button type="submit" className="dive-in-btn" disabled={loading}>
            {loading && <span className="button-spinner" aria-hidden="true" />}
            <span>{loading ? "Logging in..." : "Dive In ✦"}</span>
          </button>
        </form>

        <button type="button" className="trouble-login">
          Trouble Logging In?
        </button>
      </div>
    </div>
  );
}
