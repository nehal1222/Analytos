import React, { useEffect, useMemo, useState } from "react";
import { api } from "./api.js";

function DiffStat({ label, value, tone }) {
  return (
    <div className={`diff-stat ${tone}`}>
      <div className="diff-stat-value">{value}</div>
      <div className="diff-stat-label">{label}</div>
    </div>
  );
}

function SourceDocViewer({ filenames }) {
  const [open, setOpen] = useState(null); // filename currently expanded, or null
  const [cache, setCache] = useState({}); // filename -> text
  const [error, setError] = useState(null);

  const toggle = async (filename) => {
    if (open === filename) {
      setOpen(null);
      return;
    }
    setOpen(filename);
    if (!cache[filename]) {
      try {
        const doc = await api.sourceDoc(filename);
        setCache((c) => ({ ...c, [filename]: doc.text }));
      } catch (e) {
        setError(`${filename}: ${e.message}`);
      }
    }
  };

  return (
    <div className="source-docs">
      <h4>Source documents</h4>
      <p className="muted">
        The raw text each extraction came from -- check this against the diff below before approving.
      </p>
      {error && <p className="error">{error}</p>}
      {filenames.map((filename) => (
        <div key={filename} className="source-doc">
          <button type="button" className="link-button" onClick={() => toggle(filename)}>
            {open === filename ? "▾" : "▸"} {filename}
          </button>
          {open === filename && (
            <pre className="source-doc-body">
              {cache[filename] === undefined ? "Loading…" : cache[filename]}
            </pre>
          )}
        </div>
      ))}
    </div>
  );
}

function NodeDiffRow({ node }) {
  return (
    <li className={`diff-row ${node.change}`}>
      <div className="diff-head">
        <span className={`badge ${node.change}`}>{node.change}</span>
        <strong>{node.type}</strong>
        <code>{node.slug}</code>
      </div>
      {node.change === "insert" && (
        <pre className="diff-body">{JSON.stringify(node.after, null, 2)}</pre>
      )}
      {node.change === "update" && (
        <table className="diff-table">
          <thead>
            <tr>
              <th>field</th>
              <th>before</th>
              <th>after</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(node.changed_fields).map(([field, { before, after }]) => (
              <tr key={field}>
                <td>{field}</td>
                <td className="before">{String(before ?? "—")}</td>
                <td className="after">{String(after ?? "—")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </li>
  );
}

function RunDetail({ run, onActed, currentUser }) {
  const [diff, setDiff] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [showUnchangedNodes, setShowUnchangedNodes] = useState(false);
  const [showUnchangedEdges, setShowUnchangedEdges] = useState(false);
  const [comment, setComment] = useState("");

  useEffect(() => {
    setDiff(null);
    setShowUnchangedNodes(false);
    setShowUnchangedEdges(false);
    setComment("");
    api.runDiff(run.run_id).then(setDiff).catch((e) => setError(e.message));
  }, [run.run_id]);

  const canReview = currentUser.role === "admin" || currentUser.role === "reviewer";

  // "reaffirmed" (only source_doc changed -- the same content re-described
  // by a newer document) is low-signal just like "unchanged": collapse
  // both behind the same toggle so the default view is just the handful
  // of rows a reviewer actually needs to look at.
  const { changedNodes, lowSignalNodes, changedEdges, unchangedEdges } = useMemo(() => {
    if (!diff) return { changedNodes: [], lowSignalNodes: [], changedEdges: [], unchangedEdges: [] };
    return {
      changedNodes: diff.nodes.filter((n) => n.change === "insert" || n.change === "update"),
      lowSignalNodes: diff.nodes.filter((n) => n.change === "unchanged" || n.change === "reaffirmed"),
      changedEdges: diff.edges.filter((e) => e.change !== "unchanged"),
      unchangedEdges: diff.edges.filter((e) => e.change === "unchanged"),
    };
  }, [diff]);

  const act = async (action) => {
    setBusy(true);
    setError(null);
    try {
      if (action === "approve") await api.approveRun(run.run_id, comment);
      else await api.rejectRun(run.run_id, comment);
      onActed();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="run-detail">
      <h3>{run.branch}</h3>
      <p className="muted">
        Ingested from {run.source_docs.join(", ")} · proposed by {run.actor}
      </p>
      {run.warnings?.length > 0 && (
        <div className="warnings">
          {run.warnings.map((w, i) => (
            <div key={i}>⚠ {w}</div>
          ))}
        </div>
      )}

      <SourceDocViewer filenames={run.source_docs} />

      {(run.approved_comment || run.rejected_comment) && (
        <div className="review-comment">
          <h4>Reviewer note</h4>
          <p>{run.approved_comment || run.rejected_comment}</p>
        </div>
      )}

      {run.status === "pending_review" && canReview && (
        <div className="review-actions">
          <p className="muted">
            Acting as <strong>{currentUser.display_name}</strong> ({currentUser.role})
          </p>
          <textarea
            className="review-comment-input"
            placeholder="Optional note explaining your decision (e.g. why you rejected this, or anything a future reader should know)…"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={2}
          />
          <div className="review-actions-buttons">
            <button disabled={busy} onClick={() => act("approve")} className="approve">
              Approve → merge to main
            </button>
            <button disabled={busy} onClick={() => act("reject")} className="reject">
              Reject → discard branch
            </button>
          </div>
        </div>
      )}
      {run.status === "pending_review" && !canReview && (
        <p className="muted">Your account ({currentUser.role}) can't approve or reject runs.</p>
      )}
      {error && <p className="error">{error}</p>}

      {!diff ? (
        <p className="muted">Loading diff…</p>
      ) : (
        <>
          <div className="diff-stats">
            <DiffStat label="new nodes" value={diff.summary.nodes_inserted} tone="insert" />
            <DiffStat label="updated nodes" value={diff.summary.nodes_updated} tone="update" />
            <DiffStat label="reaffirmed nodes" value={diff.summary.nodes_reaffirmed} tone="unchanged" />
            <DiffStat label="unchanged nodes" value={diff.summary.nodes_unchanged} tone="unchanged" />
            <DiffStat label="new edges" value={diff.summary.edges_inserted} tone="insert" />
            <DiffStat label="existing edges" value={diff.summary.edges_unchanged} tone="unchanged" />
          </div>

          <h4>Nodes</h4>
          {changedNodes.length === 0 && lowSignalNodes.length === 0 && (
            <p className="muted">No node changes.</p>
          )}
          {changedNodes.length === 0 && lowSignalNodes.length > 0 && (
            <p className="muted">
              Nothing new -- every node in this run already matches main, or was only re-affirmed by
              a newer document (re-ingesting the same document(s) is idempotent).
            </p>
          )}
          <ul className="diff-list">
            {changedNodes.map((n) => (
              <NodeDiffRow key={`${n.type}-${n.slug}`} node={n} />
            ))}
          </ul>
          {lowSignalNodes.length > 0 && (
            <>
              <button type="button" className="link-button toggle-unchanged" onClick={() => setShowUnchangedNodes((v) => !v)}>
                {showUnchangedNodes ? "Hide" : "Show"} {lowSignalNodes.length} unchanged/reaffirmed node
                {lowSignalNodes.length === 1 ? "" : "s"}
              </button>
              {showUnchangedNodes && (
                <ul className="diff-list">
                  {lowSignalNodes.map((n) => (
                    <NodeDiffRow key={`${n.type}-${n.slug}`} node={n} />
                  ))}
                </ul>
              )}
            </>
          )}

          <h4>Edges</h4>
          <ul className="edge-list">
            {changedEdges.map((e, i) => (
              <li key={i} className={`badge-line ${e.change}`}>
                <span className={`badge ${e.change}`}>{e.change}</span> {e.type}: {e.src} → {e.dst}
              </li>
            ))}
          </ul>
          {changedEdges.length === 0 && unchangedEdges.length > 0 && (
            <p className="muted">No new edges -- all already present on main.</p>
          )}
          {unchangedEdges.length > 0 && (
            <>
              <button type="button" className="link-button toggle-unchanged" onClick={() => setShowUnchangedEdges((v) => !v)}>
                {showUnchangedEdges ? "Hide" : "Show"} {unchangedEdges.length} existing edge{unchangedEdges.length === 1 ? "" : "s"}
              </button>
              {showUnchangedEdges && (
                <ul className="edge-list">
                  {unchangedEdges.map((e, i) => (
                    <li key={i} className={`badge-line ${e.change}`}>
                      <span className={`badge ${e.change}`}>{e.change}</span> {e.type}: {e.src} → {e.dst}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}

function SubmitDocument({ onIngested }) {
  const [open, setOpen] = useState(false);
  const [filename, setFilename] = useState("");
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.ingest(filename.trim(), content);
      setResult(res);
      setFilename("");
      setContent("");
      onIngested();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return (
      <button type="button" className="link-button submit-doc-toggle" onClick={() => setOpen(true)}>
        + Submit a new document for review
      </button>
    );
  }

  return (
    <form className="submit-doc" onSubmit={submit}>
      <div className="submit-doc-head">
        <h3>Submit a new document</h3>
        <button type="button" className="link-button" onClick={() => setOpen(false)}>
          cancel
        </button>
      </div>
      <p className="muted">
        This never touches main -- it runs the same ingestion pipeline as the CLI, landing on its own
        review branch for someone to approve or reject.
      </p>
      <input
        type="text"
        placeholder="filename.md (must be new -- won't overwrite an existing seed doc)"
        value={filename}
        onChange={(e) => setFilename(e.target.value)}
        required
      />
      <textarea
        placeholder="Paste the document's Markdown content here…"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={10}
        required
      />
      <button type="submit" disabled={busy || !filename.trim() || !content.trim()}>
        {busy ? "Ingesting…" : "Submit for review"}
      </button>
      {error && <p className="error">{error}</p>}
      {result && (
        <pre className="submit-doc-result">{result.output}</pre>
      )}
    </form>
  );
}

function SeedBootstrap({ onSeeded }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.seedBootstrap();
      onSeeded();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="seed-bootstrap">
      <p className="muted">
        Nothing ingested yet on this instance. Load the built-in seed documents (seed-data/) as one
        review run -- you'll still approve it below before it touches main.
      </p>
      <button type="button" onClick={run} disabled={busy}>
        {busy ? "Ingesting seed data…" : "Load seed data"}
      </button>
      {error && <p className="error">{error}</p>}
    </div>
  );
}

export default function Review({ currentUser }) {
  const [runs, setRuns] = useState(null);
  const [selected, setSelected] = useState(null);

  const reload = () => {
    api.runs().then((rs) => {
      setRuns(rs);
      if (selected) {
        const still = rs.find((r) => r.run_id === selected.run_id);
        setSelected(still || null);
      }
    });
  };

  useEffect(reload, []);

  if (!runs) return <p className="muted">Loading…</p>;

  const canReview = currentUser.role === "admin" || currentUser.role === "reviewer";

  return (
    <div className="review">
      <div className="run-list">
        <h2>Ingestion Runs</h2>
        <SubmitDocument onIngested={reload} />
        {runs.length === 0 && canReview && <SeedBootstrap onSeeded={reload} />}
        {runs.length === 0 && <p className="muted">No runs yet. Run the ingestion pipeline first.</p>}
        <ul>
          {runs.map((r) => (
            <li
              key={r.run_id}
              className={r.run_id === selected?.run_id ? "active" : ""}
              onClick={() => setSelected(r)}
            >
              <span className={`badge ${r.status}`}>{r.status.replace("_", " ")}</span>
              <div>{r.branch}</div>
              <div className="muted">{r.source_docs.join(", ")}</div>
            </li>
          ))}
        </ul>
      </div>
      <div className="run-panel">
        {selected ? (
          <RunDetail run={selected} onActed={reload} currentUser={currentUser} />
        ) : (
          <p className="muted">Select a run to review its diff.</p>
        )}
      </div>
    </div>
  );
}
