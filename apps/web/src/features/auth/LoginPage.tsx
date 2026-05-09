import { useState, type FormEvent } from "react";
import { useAuth } from "./useAuth";

const QUICK_LOGINS = [
  { email: "hrbp@example.com", password: "password123", label: "HRBP" },
  { email: "admin@example.com", password: "password123", label: "Admin" },
] as const;

export default function LoginPage() {
  const { login, isLoading, error } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    login(email, password);
  };

  const handleQuickLogin = (quickEmail: string, quickPassword: string) => {
    login(quickEmail, quickPassword);
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h1 className="login-title">HR Agent</h1>
        <p className="login-subtitle">Recruitment Workspace</p>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="login-field">
            <label htmlFor="login-email">Email</label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
            />
          </div>
          <div className="login-field">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
              autoComplete="current-password"
            />
          </div>
          <button
            type="submit"
            className="login-submit"
            disabled={isLoading}
            aria-busy={isLoading}
          >
            {isLoading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <div
          className="login-status"
          role="status"
          aria-live="polite"
        >
          {isLoading && !error && "Signing in..."}
          {error && (
            <span className="login-error" role="alert">
              {error}
            </span>
          )}
        </div>

        <div className="login-quick">
          <p className="login-quick-title">Quick Sign In</p>
          <div className="login-quick-buttons">
            {QUICK_LOGINS.map((ql) => (
              <button
                key={ql.email}
                type="button"
                className="login-quick-btn"
                disabled={isLoading}
                onClick={() => handleQuickLogin(ql.email, ql.password)}
              >
                {ql.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
