"""CLI: ingest one or more seed documents into a fresh review branch.

    python ingest.py ../seed-data/*.md
    python ingest.py ../seed-data/new-doc.md

Never writes to main. Always creates exactly one new branch per invocation
(`ingest/<run-id>`), loads the extracted nodes/edges onto it with
`--mode merge` (upsert by @key -- re-running on the same document(s) never
duplicates nodes), and writes a run manifest to runs/<run_id>.json that the
review service (../review) reads to render the HITL diff.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))

from graph_schema import edge_exists  # noqa: E402
from omnigraph_client import client_for  # noqa: E402

from build_graph import build
from extract import extract
from schema_contract import ExtractionResult

RUNS_DIR = Path(__file__).resolve().parent / "runs"


def make_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]


def _resolve_docs(patterns: list[str]) -> list[Path]:
    # Bash expands a glob like `../seed-data/*.md` before this script ever
    # sees it; PowerShell does not do that for external programs, so it
    # arrives here as the literal string "*.md". Expand it ourselves so the
    # same command works in both shells.
    paths: list[Path] = []
    for pattern in patterns:
        p = Path(pattern)
        if any(ch in pattern for ch in "*?[]"):
            matches = sorted(p.parent.glob(p.name))
            if not matches:
                raise SystemExit(f"no files match pattern: {pattern}")
            paths.extend(matches)
        else:
            paths.append(p)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docs", nargs="+", help="paths to seed documents (.md), globs allowed")
    parser.add_argument("--actor", default="act-ingestion-pipeline")
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()

    run_id = make_run_id()
    branch = f"ingest/{run_id}"

    extractions: list[tuple[str, ExtractionResult]] = []
    for path in _resolve_docs(args.docs):
        text = path.read_text(encoding="utf-8")
        result = extract(text, path.name)
        extractions.append((path.name, result))
        print(
            f"extracted {path.name}: {len(result.products)}p {len(result.features)}f "
            f"{len(result.proof_points)}pp {len(result.decisions)}d {len(result.icp_segments)}seg "
            f"{len(result.personas)}per {len(result.people)}person {len(result.email_threads)}thread"
        )

    build_result = build(extractions, ingest_run=run_id)
    for w in build_result.warnings:
        print(f"WARNING: {w}")

    if not build_result.records:
        print("Nothing extracted -- aborting without creating a branch.")
        return

    client_kwargs = {"base_url": args.base_url} if args.base_url else {}
    client = client_for(args.actor, **client_kwargs)

    client.branch_create(branch, from_branch="main")

    # `load --mode merge` upserts NODE rows by @key, but edge rows have no
    # user-visible key -- re-asserting an edge that already exists (the new
    # branch is forked from main, so anything merged in a previous run is
    # already there) would create a second row and trip the edge's
    # @unique(src, dst) constraint instead of silently no-op'ing. Checking
    # against the new branch itself (not main) keeps this within what the
    # ingestion actor is allowed to read (see cluster/base.policy.yaml).
    load_records = []
    skipped_existing_edges = 0
    for rec in build_result.records:
        if "edge" in rec and edge_exists(client, rec["edge"], rec["from"], rec["to"], branch=branch):
            skipped_existing_edges += 1
            continue
        load_records.append(rec)
    if skipped_existing_edges:
        print(f"skipped {skipped_existing_edges} edge(s) already present on '{branch}'")

    load_result = client.load(load_records, branch=branch, mode="merge")

    RUNS_DIR.mkdir(exist_ok=True)
    manifest = {
        "run_id": run_id,
        "branch": branch,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "actor": args.actor,
        "source_docs": [name for name, _ in extractions],
        "node_counts": build_result.node_counts,
        "edge_counts": build_result.edge_counts,
        "warnings": build_result.warnings,
        "load_result": load_result,
        "records": build_result.records,
        "status": "pending_review",
    }
    (RUNS_DIR / f"{run_id}.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\nBranch '{branch}' created and loaded.")
    print(f"Nodes: {build_result.node_counts}")
    print(f"Edges: {build_result.edge_counts}")
    print(f"Run manifest: runs/{run_id}.json")
    print("Open the review dashboard to approve or reject this run.")


if __name__ == "__main__":
    main()
