const BASE = "/api";

// AuthError carries the HTTP status so callers (App.jsx) can tell "not
// logged in" (401) apart from any other failure and show the login screen
// specifically for that case, instead of a generic error message.
export class AuthError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function req(path, options) {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "include", // send/receive the session cookie
    ...options,
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ detail: resp.statusText }));
    const message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    if (resp.status === 401) throw new AuthError(message, 401);
    throw new Error(message);
  }
  if (resp.status === 204) return null;
  return resp.json();
}

export const api = {
  login: (username, password) =>
    req("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  signup: (username, password, displayName) =>
    req("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ username, password, display_name: displayName }),
    }),
  logout: () => req("/auth/logout", { method: "POST" }),
  me: () => req("/auth/me"),

  products: () => req("/products"),
  product: (slug) => req(`/products/${encodeURIComponent(slug)}`),
  features: () => req("/features"),
  proofPoints: () => req("/proof-points"),
  decisions: () => req("/decisions"),
  icpSegments: () => req("/icp-segments"),
  icpSegment: (slug) => req(`/icp-segments/${encodeURIComponent(slug)}`),
  personas: () => req("/personas"),
  emailThreads: () => req("/email-threads"),
  emailThread: (slug) => req(`/email-threads/${encodeURIComponent(slug)}`),
  people: () => req("/people"),
  search: (queryText) => req(`/search?query_text=${encodeURIComponent(queryText)}`),
  commits: (branch = "main") => req(`/commits?branch=${encodeURIComponent(branch)}`),
  branches: () => req("/branches"),

  runs: () => req("/runs"),
  run: (runId) => req(`/runs/${encodeURIComponent(runId)}`),
  runDiff: (runId) => req(`/runs/${encodeURIComponent(runId)}/diff`),
  // No reviewer field anymore -- the acting identity comes from the
  // session cookie, verified server-side (see auth.py / main.py). An
  // optional comment lets a reviewer record *why*, not just *who/when*.
  approveRun: (runId, comment) =>
    req(`/runs/${encodeURIComponent(runId)}/approve`, {
      method: "POST",
      body: JSON.stringify({ comment: comment || null }),
    }),
  rejectRun: (runId, comment) =>
    req(`/runs/${encodeURIComponent(runId)}/reject`, {
      method: "POST",
      body: JSON.stringify({ comment: comment || null }),
    }),
  sourceDoc: (filename) => req(`/source-docs/${encodeURIComponent(filename)}`),
  ingest: (filename, content) =>
    req("/ingest", { method: "POST", body: JSON.stringify({ filename, content }) }),
};
