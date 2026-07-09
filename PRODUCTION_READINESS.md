# Production Readiness Punch List

Written after building and verifying the POC end-to-end (see `README.md` for
architecture/design rationale). This is a prioritized list of what's
missing between "working POC" and "production" — not a redesign, the
underlying architecture (branch-per-run governance, Cedar-enforced merge
gate, real actor attribution) is sound and doesn't need to change.

## P0 — Security (do these before any real customer data touches this)

- [x] **Close the MCP-bypass gap.** ~~Today, `content-agent`'s bearer
      token has unconditional `invoke_query` in Cedar~~ — fixed via
      `mcp-server/gateway.py`: `act-content-agent`/`act-gtm-agent` are no
      longer real Cedar actors at all (removed from `tokens.dev.json` and
      `base.policy.yaml`); only a new `act-query-gateway` service actor
      has `read`(main)/`invoke_query`, and only the gateway process holds
      its token. Agent-facing "tokens" are now gateway API keys
      (`policy.yaml`'s `gateway_api_key`) that authenticate to the gateway,
      which allowlists query names per role and never accepts ad-hoc query
      text at all. Verified: `demo_policy_check.py` confirms
      `act-content-agent` resolves no bearer token, and the gateway 403s a
      disallowed query while allowing a permitted one. This was worse than
      first assessed -- the ad-hoc query endpoint only checks `read` on the
      branch, so the old model let any agent token submit hand-written
      `.gq` text and read `EmailThread` directly, not just call the wrong
      named query.
- [ ] **Real auth on the console.** ~~The "sign in as reviewer" dropdown is
      a client-side label~~ -- fixed: real login (`console/backend/auth.py`,
      bcrypt + JWT session cookies, `manage_users.py` to provision
      accounts), approve/reject now derive the acting identity from the
      verified session, not a request body field. Still open: no
      rate-limiting on login attempts, and the session secret falls back to
      a locally-generated dev file if `SESSION_SECRET` isn't set explicitly.
- [ ] **Replace `tokens.dev.json`** with a real secrets-manager-backed
      token source (`OMNIGRAPH_SERVER_BEARER_TOKENS_AWS_SECRET`, or
      equivalent) and rotate every dev token that's currently checked in.
- [ ] **TLS everywhere.** Everything currently runs on plain HTTP — the
      Omnigraph server, the console backend, the MCP servers all need to
      sit behind TLS termination before any token crosses a real network.
- [ ] **Lock down CORS** on the console backend (`allow_origins=["*"]`
      today) to the actual dashboard origin.

## P1 — Reliability / Ops

- [ ] **Write an actual test suite.** Everything was verified manually in
      one interactive session — no unit tests for `build_graph.py`'s
      dedup/resolution logic, no integration test that ingest → review →
      merge → dashboard read stays correct, no regression protection at
      all. Start with: idempotent re-ingestion, edge-existence dedup,
      Cedar-deny-path assertions (already scripted informally in
      `agents/demo_policy_check.py` — turn that into a real pytest suite).
- [ ] **Release builds, not debug.** `cargo build --release` behaves
      differently from the debug build used throughout this POC (smaller
      stack frames — the debug binaries needed `editbin /STACK:...` just to
      not crash on startup). Build and test against release binaries
      before deploying.
- [ ] **Process supervision.** Nothing here restarts on crash — no
      systemd/Docker/supervisor config. Containerize `omnigraph-server`,
      the console backend, and the MCP servers with real restart policies
      and health checks (the server already exposes `/healthz`).
- [ ] **Log aggregation + error tracking.** Right now it's whatever prints
      to stdout in each terminal. Needs structured logging shipped
      somewhere queryable, plus error tracking (Sentry or equivalent) on
      the Python services.
- [ ] **A real schema-migration plan.** Already hit this once during
      setup — changing a column's nullability isn't a supported migration
      (`OG-MF-106`), and the fix was wiping the graph and reapplying from
      scratch. That's fine pre-launch; it is not fine once `main` holds
      real approved knowledge. Plan schema changes as additive-only where
      possible, and rehearse migrations against a snapshot before applying
      to the real graph.
- [ ] **Backups / DR for the graph store.** Currently local `file://`
      storage, single copy, no replication, no backup job. Move to S3 (the
      engine already supports it — see `cluster.yaml`'s `storage:` option)
      with versioning/backup enabled before this is the source of truth
      for anything real.

## P2 — Scale / data quality

- [ ] **Load-test ingestion and diffing at real volume.** Verified at toy
      scale (2 products, ~40 nodes total). The diff computation does one
      HTTP round-trip per node/edge to check existence — fine for dozens
      of rows, needs batching or a real diff API before hundreds/thousands.
- [ ] **Swap the mock embedding provider for a real one**
      (`providers.embedding.default.kind: openai-compatible` or `gemini` in
      `cluster.yaml`) — the mock provider gives no real semantic search,
      only exact-string-hash similarity; `bm25()` is doing all the real
      relevance work today.
- [ ] **Harden the LLM extraction path.** No retry logic for transient API
      failures, no handling for an LLM response that doesn't validate
      against `ExtractionResult`'s pydantic schema beyond letting it raise.
      Add retries + a repair/re-prompt step for malformed extraction output.
- [ ] **Concurrency.** Two ingestion runs forking from `main` at the same
      time aren't tested — worth understanding the failure mode (or adding
      a lock) before multiple people run the pipeline simultaneously.

## P3 — Engineering hygiene

- [ ] CI pipeline (lint, typecheck, the new test suite, a build check).
- [ ] Multi-tenancy story if this ever needs to serve more than one graph
      per deployment (currently single-graph, single-tenant by design).
- [ ] Rate limiting / abuse protection on the console backend itself (the
      Omnigraph server already has per-actor inflight/byte limits; the
      FastAPI layer in front of it doesn't).
