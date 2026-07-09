import React, { useEffect, useState } from "react";
import { api } from "./api.js";

function fmtTime(microsOrIso) {
  if (typeof microsOrIso === "number") {
    return new Date(microsOrIso / 1000).toLocaleString();
  }
  if (typeof microsOrIso === "string") {
    return new Date(microsOrIso).toLocaleString();
  }
  return "—";
}

export default function Changes() {
  const [commits, setCommits] = useState(null);
  const [runs, setRuns] = useState(null);

  useEffect(() => {
    api.commits("main").then(setCommits).catch(() => setCommits([]));
    api.runs().then(setRuns).catch(() => setRuns([]));
  }, []);

  const pending = (runs || []).filter((r) => r.status === "pending_review");

  return (
    <div className="changes">
      <h2>Recent Changes</h2>

      {pending.length > 0 && (
        <>
          <h3>Awaiting review</h3>
          <ul className="commit-list">
            {pending.map((r) => (
              <li key={r.run_id} className="commit pending">
                <span className="badge pending">pending review</span>
                <strong>{r.branch}</strong>
                <span className="muted"> from {r.source_docs.join(", ")}</span>
                <div className="muted">{fmtTime(r.created_at)} · proposed by {r.actor}</div>
              </li>
            ))}
          </ul>
        </>
      )}

      <h3>Merged commits on main</h3>
      {!commits ? (
        <p className="muted">Loading…</p>
      ) : commits.length === 0 ? (
        <p className="muted">No commits yet.</p>
      ) : (
        <ul className="commit-list">
          {commits.map((c) => (
            <li key={c.graph_commit_id} className="commit">
              <span className="badge merged">merged</span>
              <code>{c.graph_commit_id.slice(0, 8)}</code>
              <span className="muted"> by {c.actor_id || "unknown"}</span>
              {c.merged_parent_commit_id && <span className="badge merge-tag">merge</span>}
              <div className="muted">{fmtTime(c.created_at)}</div>
            </li>
          ))}
        </ul>
      )}

      <h3>All ingestion runs</h3>
      <p className="muted">
        Every run, its full attribution trail, and any reviewer note -- the audit record for
        "who changed what, and why" that governance actually depends on.
      </p>
      {!runs ? (
        <p className="muted">Loading…</p>
      ) : (
        <ul className="commit-list">
          {runs.map((r) => (
            <li key={r.run_id} className="commit">
              <div className="commit-head">
                <span className={`badge ${r.status}`}>{r.status.replace("_", " ")}</span>
                <strong>{r.branch}</strong>
              </div>
              <div className="muted">
                {r.source_docs.join(", ")} · {r.node_counts && Object.values(r.node_counts).reduce((a, b) => a + b, 0)} nodes,{" "}
                {r.edge_counts && Object.values(r.edge_counts).reduce((a, b) => a + b, 0)} edges · proposed by {r.actor} at{" "}
                {fmtTime(r.created_at)}
              </div>
              {r.status === "merged" && (
                <div className="muted">approved by <strong>{r.approved_by}</strong> at {fmtTime(r.approved_at)}</div>
              )}
              {r.status === "rejected" && (
                <div className="muted">rejected by <strong>{r.rejected_by}</strong> at {fmtTime(r.rejected_at)}</div>
              )}
              {(r.approved_comment || r.rejected_comment) && (
                <div className="commit-note">"{r.approved_comment || r.rejected_comment}"</div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
