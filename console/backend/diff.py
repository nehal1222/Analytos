"""Row-level diff between a pending ingest branch and `main`.

OmniGraph's engine-level `diff_between`/`ChangeSet` (Git-style three-way
diff) is not exposed over HTTP as of the version vendored in this repo
(confirmed by reading crates/omnigraph/src/changes/mod.rs vs.
crates/omnigraph-server/src/handlers.rs -- no `/diff` route exists). Since
the ingestion pipeline already knows exactly which node/edge rows it
proposed (stored verbatim in the run manifest as `records`), this module
reconstructs an equivalent diff by looking each proposed row up on `main`
by its `@key` (slug) and comparing field-by-field -- exactly what a human
reviewer needs to see, without needing the engine's internal ChangeSet API.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared"))

from graph_schema import edge_exists  # noqa: E402

NODE_FIELDS: dict[str, list[str]] = {
    "Product": ["slug", "name", "category", "summary", "source_doc", "ingest_run"],
    "Feature": ["slug", "name", "description", "source_doc", "ingest_run"],
    "ProofPoint": [
        "slug", "label", "value", "metric_type", "baseline", "description",
        "source_doc", "ingest_run",
    ],
    "Persona": ["slug", "title", "role_level", "description", "source_doc", "ingest_run"],
    "ICPSegment": [
        "slug", "name", "firmographics", "tech_signals", "trigger_signals",
        "competitor_angle", "source_doc", "ingest_run",
    ],
    "Person": ["slug", "name", "email", "company", "role", "source_doc", "ingest_run"],
    "EmailThread": [
        "slug", "thread_id", "subject", "summary", "internal_only", "occurred_at",
        "source_doc", "ingest_run",
    ],
    "Decision": [
        "slug", "title", "description", "status", "decided_at", "source_doc", "ingest_run",
    ],
}

def _get_node(client, node_type: str, slug: str, branch: str) -> dict[str, Any] | None:
    fields = NODE_FIELDS[node_type]
    projection = ", ".join(f"$n.{f} as {f}" for f in fields)
    source = (
        f"query get_node($slug: String) {{ "
        f"match {{ $n: {node_type} {{ slug: $slug }} }} "
        f"return {{ {projection} }} }}"
    )
    result = client.ad_hoc_query(source, {"slug": slug}, branch=branch)
    rows = result.get("rows") or []
    return rows[0] if rows else None


# Pipeline bookkeeping, not graph content -- every re-ingestion of an
# unchanged document naturally stamps a new `ingest_run`, so treating it as
# a "change" would make truly idempotent re-ingestion look like an update
# on every field, which is misleading to a reviewer.
_BOOKKEEPING_FIELDS = {"ingest_run"}

# A node whose *only* changed field is source_doc was re-affirmed by a
# newer document, not actually edited -- e.g. re-describing an existing
# product in an update doc touches every one of its existing features'
# source_doc without changing anything about them. Lumping that in with
# real "update"s buries the handful of genuinely new/changed fields under a
# wall of low-signal provenance-only rows, so it gets its own bucket.
_PROVENANCE_ONLY_FIELDS = {"source_doc"}


def compute_diff(manifest: dict[str, Any], client, base_branch: str = "main") -> dict[str, Any]:
    node_diffs: list[dict[str, Any]] = []
    edge_diffs: list[dict[str, Any]] = []

    for rec in manifest.get("records", []):
        if "type" in rec:
            node_type, data = rec["type"], rec["data"]
            slug = data["slug"]
            existing = _get_node(client, node_type, slug, base_branch)
            if existing is None:
                node_diffs.append(
                    {"type": node_type, "slug": slug, "change": "insert", "before": None, "after": data}
                )
            else:
                changed = {
                    k: {"before": existing.get(k), "after": v}
                    for k, v in data.items()
                    if k not in _BOOKKEEPING_FIELDS and existing.get(k) != v
                }
                if not changed:
                    change = "unchanged"
                elif set(changed) <= _PROVENANCE_ONLY_FIELDS:
                    change = "reaffirmed"
                else:
                    change = "update"
                node_diffs.append(
                    {
                        "type": node_type,
                        "slug": slug,
                        "change": change,
                        "before": existing,
                        "after": data,
                        "changed_fields": changed,
                    }
                )
        elif "edge" in rec:
            edge_type, src, dst = rec["edge"], rec["from"], rec["to"]
            exists = edge_exists(client, edge_type, src, dst, base_branch)
            edge_diffs.append(
                {"type": edge_type, "src": src, "dst": dst, "change": "unchanged" if exists else "insert"}
            )

    summary = {
        "nodes_inserted": sum(1 for n in node_diffs if n["change"] == "insert"),
        "nodes_updated": sum(1 for n in node_diffs if n["change"] == "update"),
        "nodes_reaffirmed": sum(1 for n in node_diffs if n["change"] == "reaffirmed"),
        "nodes_unchanged": sum(1 for n in node_diffs if n["change"] == "unchanged"),
        "edges_inserted": sum(1 for e in edge_diffs if e["change"] == "insert"),
        "edges_unchanged": sum(1 for e in edge_diffs if e["change"] == "unchanged"),
    }
    return {"summary": summary, "nodes": node_diffs, "edges": edge_diffs}
