# Analytos Context Layer — Omnigraph POC

A governed, single-source-of-truth knowledge layer for Analytos, built on
the open-source [Omnigraph](https://github.com/ModernRelay/omnigraph) engine
(checked out as a sibling directory, `../omnigraph`). Demonstrates the full
loop: **ingest → LLM extract → human review (HITL) → merge to main → serve
via dashboard + MCP → agents produce real work from it.**

```
seed-data/*.md
     │
     ▼
pipeline/ingest.py  (parse → LLM extract → branch → load --mode merge)
     │  creates branch ingest/<run-id>, never touches main
     ▼
console (React + FastAPI)
  ├─ Review Queue: diff, approve → merge to main / reject → discard branch
  ├─ Dashboard: entity browser, hybrid search, recent changes
     │
     ▼  (only after merge — agents can't read a branch under review)
mcp-server/mcp_server.py --role {content-agent,gtm-agent}
     │
     ▼
agents/{content_agent.py, gtm_agent.py}  (Claude + MCP tool use)
```

## Repo layout

```
poc/
  cluster/            knowledge.pg (schema), queries/*.gq, base.policy.yaml (Cedar),
                       cluster.yaml, tokens.dev.json (dev bearer tokens)
  seed-data/           the 5 seed documents (fabricated for this POC — see below)
  pipeline/            ingestion: extract.py, build_graph.py, slugs.py, ingest.py
  console/backend/     FastAPI: dashboard reads + HITL review/diff/approve/reject
  console/frontend/    React (Vite): Dashboard, Recent Changes, Review Queue pages
  mcp-server/          MCP server exposing stored queries as role-scoped tools
  agents/              content_agent.py, gtm_agent.py, demo_policy_check.py
  shared/              omnigraph_client.py (HTTP client), mock_embedding.py
```

## Seed data note

The brief names five seed documents but doesn't ship their content, so
`seed-data/*.md` was written for this POC: a fictional product-overview doc
each for **Stockly** (inventory/demand forecasting) and **Inspectly**
(AI visual inspection for regulated manufacturing), an ICP doc, and two
internal email threads (one per product) that include a pilot customer name
and metrics — the deliberately internal/sensitive content the access-control
demo (Use Case A) is built around.

## Prerequisites

- Rust (`cargo build --workspace --locked` in `../omnigraph`; needs no
  `protoc` in this checkout — the earlier `AGENTS.md` note about `protoc`
  did not turn out to be a hard build requirement in practice).
- Python 3.11+ , Node 18+.
- No external API keys are required to run the full loop end-to-end — see
  "Mock providers" below. Set `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` for
  the real (non-mock) extraction and agent paths.

## Setup

### 1. Build and install the Omnigraph CLI/server

```bash
cd ../omnigraph
cargo build --workspace --locked --release
export PATH="$PWD/target/release:$PATH"   # or copy the two binaries onto PATH
```

### 2. Bring up the cluster (local `file://` storage, no S3 needed for the POC)

```bash
cd poc/cluster
omnigraph cluster validate --config .
omnigraph cluster import   --config .
omnigraph cluster plan     --config .
omnigraph cluster apply    --config .
```

This creates `poc/cluster/graphs/knowledge.omni` (empty, schema applied) and
registers the stored queries + policy bundle in the cluster's state ledger.

### 3. Start the server with the dev bearer tokens

```bash
export OMNIGRAPH_SERVER_BEARER_TOKENS_FILE="$PWD/tokens.dev.json"
omnigraph-server --cluster . --bind 0.0.0.0:8080
```

`tokens.dev.json` maps opaque dev tokens to the actor ids in
`base.policy.yaml` (`act-admin`, `act-ingestion-pipeline`,
`act-reviewer-{dana,priya,ashok}`, `act-content-agent`, `act-gtm-agent`).
**Replace this file before any real deployment** — see "Security notes".

### 4. Install POC dependencies

```bash
cd poc
python -m venv .venv && source .venv/Scripts/activate   # or .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cd console/frontend && npm install
```

### 5. Run the console (dashboard + review)

```bash
# terminal A
cd poc/console/backend && uvicorn main:app --port 8000

# terminal B
cd poc/console/frontend && npm run dev
```

Open http://localhost:5173 — **Dashboard**, **Recent Changes**, and
**Review Queue** tabs.

### 6. Ingest the seed data (creates a review branch, never touches main)

```bash
cd poc/pipeline
python ingest.py ../seed-data/*.md
```

Prints extraction counts per doc and a branch name
(`ingest/<timestamp>-<hash>`). Open **Review Queue** in the console, pick
the run, inspect the diff (every proposed node/edge, insert vs. update vs.
unchanged), sign in as a reviewer (Dana / Priya / Ashok), and **Approve** to
merge into `main` (or **Reject** to discard the branch). Nothing is visible
to agents until this step completes.

Re-running `python ingest.py ../seed-data/*.md` again is safe — slugs are
derived deterministically (see `pipeline/slugs.py`), and `load --mode merge`
upserts by `@key`, so no duplicate nodes are created.

### 7. Start the query gateway (required before any agent/MCP use)

```bash
cd poc/mcp-server
python gateway.py
```

Starts on `127.0.0.1:8090`. This is the only process that holds a real
omnigraph-server credential (`act-query-gateway`) on an agent's behalf --
`act-content-agent`/`act-gtm-agent` are gateway API keys now, not Cedar
actors, and have zero power against omnigraph-server directly. See
`mcp-server/gateway.py`'s docstring for why this exists: Cedar's
`invoke_query` has no per-query scope and the ad-hoc query endpoint only
checks `read`, so the old model (agent processes holding real bearer
tokens) meant a leaked token was a leaked, fully-capable credential
regardless of what the MCP tool catalog exposed.

### 8. Verify access control with no LLM required

```bash
cd poc/agents
python demo_policy_check.py
```

Confirms (a) neither agent role's MCP tool catalog includes any
EmailThread-touching query, (b) `act-content-agent`/`act-gtm-agent` don't
resolve to any real bearer token at all, and (c) the gateway itself blocks
a disallowed query (`list_email_threads`) for content-agent's key while
allowing a permitted one -- the actual enforcement point now, not just
tool-catalog curation.

### 9. Run the two agent use cases (needs `ANTHROPIC_API_KEY` or `GEMINI_API_KEY`)

```bash
cd poc/agents
python content_agent.py "demand forecasting for mid-market retail"
python gtm_agent.py "Stockly"
```

Each spawns its own role-scoped MCP server subprocess
(`mcp-server/mcp_server.py --role ...`), which calls the query gateway
(step 7) for every tool invocation -- so the gateway must already be
running.

Provider is auto-selected: Claude (Anthropic Messages API) if
`ANTHROPIC_API_KEY` is set, Gemini (`google-genai` + function calling,
model `gemini-2.5-flash` by default) if only `GEMINI_API_KEY` is set. Force
one explicitly with `AGENT_LLM_PROVIDER=claude` or `AGENT_LLM_PROVIDER=gemini`.
Both drive the identical MCP session and tool catalog (see
`agents/mcp_agent_runner.py`) -- only the model-facing tool-call wire
format differs, so the access-control story is identical either way.

To use these as MCP servers from Claude Desktop/Code directly instead,
point an MCP client config at:

```json
{
  "mcpServers": {
    "analytos-content-agent": { "command": "python", "args": ["poc/mcp-server/mcp_server.py", "--role", "content-agent"] },
    "analytos-gtm-agent":     { "command": "python", "args": ["poc/mcp-server/mcp_server.py", "--role", "gtm-agent"] }
  }
}
```

## Design decisions & tradeoffs

**Mock embedding provider, server-side auto-embed.** `cluster.yaml`
configures the `mock` embedding provider (deterministic, hash-based, no API
key — see `crates/omnigraph/src/embedding.rs::mock_embedding`). Every
`search_*` stored query (`cluster/queries/search.gq`) takes a single plain
`$q: String` parameter and calls `nearest($x.embedding, $q)` — the engine
auto-embeds that string server-side via the configured provider before
ranking, so callers (the dashboard, the MCP search tools) never construct or
handle a raw vector themselves. This also isn't optional for the MCP path:
the server logs a startup warning if an MCP-exposed query declares a
`Vector(N)` parameter directly, since an LLM tool-caller can only supply
JSON-primitive arguments, never a raw embedding. With the `mock` provider
this only gives exact/near-exact string-hash similarity, not real semantic
similarity — the `bm25()` term of each hybrid query does the real relevance
work in this POC. Swap `providers.embedding.default.kind` in `cluster.yaml`
to `openai-compatible` or `gemini` (+ set the matching API key) for real
semantic search quality; nothing else changes, since `nearest()`/`bm25()`/`rrf()`
are already wired end-to-end.

**Diff reconstruction instead of the engine's native diff API.**
Omnigraph's `diff_between`/`ChangeSet` (a real three-way, row-level Git-style
diff) is engine-internal only — reading
`crates/omnigraph-server/src/handlers.rs` against `crates/omnigraph/src/changes/mod.rs`
confirms there is no `/diff` HTTP route in this version. Since the
ingestion pipeline already knows exactly which rows it proposed (the run
manifest stores them verbatim), `console/backend/diff.py` reconstructs an
equivalent diff by looking each proposed row up on `main` by its `@key` and
comparing field-by-field. This is arguably *more* useful for HITL review
than a generic branch diff (it's framed as "what did this ingestion run
propose", not "what changed between two arbitrary branches"), but it does
mean the diff view is specific to pipeline-authored runs, not a general
`branch A vs branch B` tool.

**MCP-gateway-level policy, on top of native Cedar.** Reading
`crates/omnigraph-policy`, Cedar's native grain in this engine version is
per-graph/per-branch (`read`, `change`, `branch_merge`, ...) — there is no
per-node-type or per-stored-query scope yet (the server's own OpenAPI spec
says so verbatim for `GET /queries`: *"Not Cedar-filtered per query yet ...
a known gap until per-query authorization lands"*). So "content-agent can
read products/proof-points but not EmailThread" — an entity-**type**-level
rule — can't be expressed in `cluster/base.policy.yaml` alone. Two layers
enforce it together:

1. **`cluster/base.policy.yaml` (real Cedar, branch-grained):** the
   `agents` group (`act-content-agent`, `act-gtm-agent`) is only granted
   `read`/`invoke_query` with `branch_scope: protected` (i.e. `main`).
   Ingestion can only write to non-main branches; only `reviewers`/`admins`
   can `branch_merge` into `main`. This alone guarantees "agents can only
   see it after merge" mechanically, and that no write lands on `main`
   without a `reviewers`-group actor performing the merge.
2. **`mcp-server/policy.yaml` (this POC's own gateway policy, same
   actor/role shape):** curates which *stored queries* each role's MCP
   server exposes as tools at all. The content-agent process never
   registers a query that touches `EmailThread` — there's no tool call
   through which it could even ask, regardless of what the Cedar layer
   would additionally block.

`agents/demo_policy_check.py` exercises both layers independently.

**Deterministic slugs, not LLM-generated ids.** LLM output is not
run-to-run deterministic, so trusting it for a node's `@key` would break
idempotent re-ingestion. `pipeline/slugs.py` always derives `slug` from a
natural key (product name, feature name scoped to its product, etc.) in
plain Python; the LLM/mock extractor only ever supplies human-readable
fields, never ids.

**Dev bearer tokens.** `cluster/tokens.dev.json` is checked in for local
demo convenience only (`OMNIGRAPH_SERVER_BEARER_TOKENS_FILE`). Replace with
a real secrets-manager-backed token source before any non-local deployment
— see `docs/user/operations/server.md` in the engine repo for the
`OMNIGRAPH_SERVER_BEARER_TOKENS_AWS_SECRET` path.

## Evaluating governance correctness

- Every ingestion run is its own branch (`ingest/<run-id>`); `pipeline/ingest.py`
  never calls `branch_merge` — only the console's `/api/runs/{id}/approve`
  endpoint does, and only as one of the three named reviewer actors.
- Re-run step 6 on the same documents and confirm node/edge counts in the
  new run's diff are all `unchanged` (or `update` only if you edited a seed
  doc) — never new duplicate nodes.
- `GET /api/commits` (Recent Changes tab) shows `actor_id` per commit —
  attribution is real, resolved server-side from the reviewer's bearer
  token, never client-supplied.

## Out of scope (per the brief)

No live Gmail/Drive/Slack connectors (seed files simulate this), no
dashboard SSO (a "sign in as reviewer" selector stands in for the review
flow's actor selection; no auth is enforced on the dashboard itself), no
production hardening/scale testing.
