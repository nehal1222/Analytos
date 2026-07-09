"""Query gateway: the only process that ever holds a real omnigraph-server
credential on an agent's behalf.

The gap this closes: Cedar's `invoke_query` has no per-query scope (an
allow grants *every* stored query on the graph), and the ad-hoc query
endpoint only checks `read` on the branch -- so any actor with read access
on main could submit hand-written .gq text and read EmailThread nodes
directly, regardless of what an MCP tool catalog exposes. Handing
`act-content-agent`'s real bearer token to the content-agent process meant
a leaked token was a leaked, fully-capable credential.

Now: `act-content-agent` / `act-gtm-agent` are not omnigraph-server Cedar
actors at all (see cluster/base.policy.yaml -- only `act-query-gateway`
is). Agent processes hold a `gateway_api_key` (policy.yaml) that
authenticates ONLY to this gateway. This gateway:

  1. maps that key to a role and its `allowed_queries` list (policy.yaml),
  2. rejects any query_name not on that list,
  3. never accepts ad-hoc query text at all (no such endpoint exists here),
  4. only then calls the real omnigraph-server, using its own
     `act-query-gateway` credential, always against `main`.

A fully leaked `dev-gwkey-content-agent` now gets an attacker exactly the
same access the content-agent MCP tools already exposed -- nothing more --
because that's structurally the only thing this service will do with it.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))
from omnigraph_client import OmniGraphError, client_for  # noqa: E402

POLICY_PATH = Path(__file__).resolve().parent / "policy.yaml"
GATEWAY_ACTOR = os.environ.get("QUERY_GATEWAY_ACTOR", "act-query-gateway")

app = FastAPI(title="Analytos Query Gateway")
_client = None


def _load_policy() -> dict[str, Any]:
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))


def _role_for_key(api_key: str) -> tuple[str, dict[str, Any]] | None:
    policy = _load_policy()
    for role_name, cfg in policy["roles"].items():
        if cfg["gateway_api_key"] == api_key:
            return role_name, cfg
    return None


@app.on_event("startup")
def _startup() -> None:
    global _client
    _client = client_for(GATEWAY_ACTOR)


class InvokeRequest(BaseModel):
    query_name: str
    params: dict[str, Any] = {}


@app.post("/invoke")
def invoke(body: InvokeRequest, authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    api_key = authorization.removeprefix("Bearer ").strip()

    match = _role_for_key(api_key)
    if match is None:
        raise HTTPException(401, "invalid gateway API key")
    role_name, role_cfg = match

    if body.query_name not in role_cfg["allowed_queries"]:
        raise HTTPException(
            403, f"role '{role_name}' is not permitted to invoke query '{body.query_name}'"
        )

    try:
        # Always main, always a pre-vetted named query -- there is no
        # parameter or code path here that accepts raw .gq text or a
        # caller-chosen branch.
        return _client.invoke_query(body.query_name, body.params, branch="main")
    except OmniGraphError as e:
        raise HTTPException(status_code=e.status, detail=e.payload) from e


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
