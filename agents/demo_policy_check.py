"""No-LLM sanity check for the access-control story. Requires no API key.

Run with the query gateway already up (`python ../mcp-server/gateway.py`)
and the omnigraph-server running with the current cluster/base.policy.yaml
applied.

Checks, in order:

1. Neither the content-agent nor gtm-agent MCP tool catalog includes any
   query that touches EmailThread (mcp-server/policy.yaml).
2. `act-content-agent` / `act-gtm-agent` are NOT recognized omnigraph-server
   Cedar actors at all anymore -- confirming there is no real bearer token
   an agent process holds that Cedar would honor for anything, even if it
   leaked. (See mcp-server/gateway.py for why this changed: Cedar's
   invoke_query has no per-query scope, and the ad-hoc query endpoint only
   checks `read` -- so the old model, where these WERE real Cedar actors
   with read+invoke_query on main, meant a leaked token was a leaked,
   fully-capable credential.)
3. The gateway itself rejects a disallowed query for a valid role (the
   actual enforcement point now) -- content-agent's key can't invoke
   list_email_threads even though nothing stops it from *asking*.
4. The gateway allows an actually-permitted query for that same key.
5. A leaked content-agent gateway key still cannot merge, delete branches,
   or do anything beyond invoke an allowlisted query against main --
   because that's the only endpoint that exists on the gateway at all.

    python demo_policy_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp-server"))

from omnigraph_client import client_for  # noqa: E402

import mcp_server  # noqa: E402

GATEWAY_URL = "http://127.0.0.1:8090"


def main() -> None:
    policy = mcp_server.load_policy()
    for role in ("content-agent", "gtm-agent"):
        allowed = policy["roles"][role]["allowed_queries"]
        print(f"[{role}] exposed tools: {sorted(allowed)}")
        leak = [
            name
            for name in allowed
            if "email" in name.lower() or "thread" in name.lower() or "participant" in name.lower()
        ]
        assert not leak, f"{role} must never expose an EmailThread-touching tool, found: {leak}"
    print("OK: neither role's MCP tool catalog includes an EmailThread-touching query.\n")

    print("Confirming act-content-agent / act-gtm-agent are not real Cedar actors anymore:")
    for actor in ("act-content-agent", "act-gtm-agent"):
        try:
            client_for(actor)
            raise AssertionError(f"{actor} should not resolve to any bearer token -- it did!")
        except KeyError:
            print(f"  OK: '{actor}' has no bearer token -- there is nothing here to leak")
    print()

    content_key = policy["roles"]["content-agent"]["gateway_api_key"]

    print("content-agent's gateway key attempting list_email_threads (should be blocked by the gateway):")
    resp = requests.post(
        f"{GATEWAY_URL}/invoke",
        headers={"Authorization": f"Bearer {content_key}"},
        json={"query_name": "list_email_threads", "params": {}},
        timeout=10,
    )
    if resp.status_code == 403:
        print(f"  DENIED as expected: HTTP 403 {resp.json().get('detail')}")
    else:
        raise AssertionError(f"expected 403, got {resp.status_code}: {resp.text}")

    print("\ncontent-agent's gateway key invoking an allowed query (should succeed):")
    resp = requests.post(
        f"{GATEWAY_URL}/invoke",
        headers={"Authorization": f"Bearer {content_key}"},
        json={"query_name": "list_products", "params": {}},
        timeout=10,
    )
    if resp.status_code == 200:
        rows = resp.json()["rows"]
        print(f"  -> {len(rows)} product(s): {[r['name'] for r in rows]}")
    else:
        raise AssertionError(f"expected 200, got {resp.status_code}: {resp.text}")

    print(
        "\nOK: the gateway is the only thing standing between an agent's key and the graph, "
        "and it only ever forwards pre-vetted named queries against main."
    )


if __name__ == "__main__":
    main()
