import React, { useEffect, useState } from "react";
import Home from "./Home.jsx";
import Tutorial from "./Tutorial.jsx";
import Dashboard from "./Dashboard.jsx";
import Review from "./Review.jsx";
import Changes from "./Changes.jsx";
import Login from "./Login.jsx";
import { api, AuthError } from "./api.js";

const TABS = [
  { key: "home", label: "Home", Component: Home },
  { key: "tutorial", label: "Tutorial", Component: Tutorial },
  { key: "dashboard", label: "Dashboard", Component: Dashboard },
  { key: "changes", label: "Recent Changes", Component: Changes },
  { key: "review", label: "Review Queue", Component: Review },
];

export default function App() {
  const [tab, setTab] = useState("home");
  const [user, setUser] = useState(null);
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch((err) => {
        if (!(err instanceof AuthError)) console.error(err);
      })
      .finally(() => setCheckingSession(false));
  }, []);

  const logout = async () => {
    await api.logout().catch(() => {});
    setUser(null);
  };

  if (checkingSession) return null; // avoid a login-screen flash while /auth/me resolves
  if (!user) return <Login onLogin={setUser} />;

  const Active = TABS.find((t) => t.key === tab).Component;

  return (
    <div className="app">
      <header className="app-header">
        <h1>GroundTruth Context Layer</h1>
        <nav className="tabs">
          {TABS.map((t) => (
            <button key={t.key} className={t.key === tab ? "active" : ""} onClick={() => setTab(t.key)}>
              {t.label}
            </button>
          ))}
        </nav>
        <div className="session-info">
          <span>
            {user.display_name} <span className="muted">({user.role})</span>
          </span>
          <button type="button" className="link-button" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>
      <main>
        <Active currentUser={user} onNavigate={setTab} />
      </main>
    </div>
  );
}
