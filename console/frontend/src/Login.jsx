import React, { useState } from "react";
import { api } from "./api.js";

export default function Login({ onLogin }) {
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const switchMode = (next) => {
    setMode(next);
    setError(null);
  };

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user =
        mode === "signup"
          ? await api.signup(username, password, displayName)
          : await api.login(username, password);
      onLogin(user);
    } catch (err) {
      setError(err.message || `${mode} failed`);
    } finally {
      setSubmitting(false);
    }
  };

  const canSubmit =
    mode === "login" ? username && password : username && password && displayName;

  return (
    <div className="login-screen">
      <form className="login-form" onSubmit={submit}>
        <h1>GroundTruth Context Layer</h1>
        <p className="muted">
          {mode === "login" ? "Sign in to continue." : "Create a read-only viewer account."}
        </p>
        <input
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
        />
        {mode === "signup" && (
          <input
            type="text"
            placeholder="Display name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
          />
        )}
        <div className="password-row">
          <input
            type={showPassword ? "text" : "password"}
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button
            type="button"
            className="link-button"
            onClick={() => setShowPassword((v) => !v)}
            tabIndex={-1}
          >
            {showPassword ? "Hide" : "Show"}
          </button>
        </div>
        <button type="submit" disabled={submitting || !canSubmit}>
          {submitting
            ? mode === "login"
              ? "Signing in…"
              : "Creating account…"
            : mode === "login"
              ? "Sign in"
              : "Create account"}
        </button>
        {error && <p className="error">{error}</p>}
        <p className="muted login-switch">
          {mode === "login" ? (
            <>
              No account?{" "}
              <button type="button" className="link-button" onClick={() => switchMode("signup")}>
                Sign up
              </button>{" "}
              for read-only access.
            </>
          ) : (
            <>
              Already have an account?{" "}
              <button type="button" className="link-button" onClick={() => switchMode("login")}>
                Sign in
              </button>
              .
            </>
          )}
        </p>
      </form>
    </div>
  );
}
