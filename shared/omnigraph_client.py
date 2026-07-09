"""Thin HTTP client for a cluster-served omnigraph-server instance.

Every write in this POC is attributed by which bearer token the caller
holds -- the server resolves that token to a Cedar actor identity itself
(never client-supplied), so this client just needs the right token per
role. See poc/cluster/base.policy.yaml for the actor/group model and
poc/README.md for how tokens map to actors in this POC's dev setup.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

import requests

DEFAULT_BASE_URL = os.environ.get("OMNIGRAPH_SERVER_URL", "http://127.0.0.1:8080")
DEFAULT_GRAPH_ID = os.environ.get("OMNIGRAPH_GRAPH_ID", "knowledge")


class OmniGraphError(RuntimeError):
    def __init__(self, status: int, payload: dict[str, Any]):
        self.status = status
        self.payload = payload
        super().__init__(f"omnigraph server error {status}: {payload}")


@dataclass
class OmniGraphClient:
    token: str
    base_url: str = DEFAULT_BASE_URL
    graph_id: str = DEFAULT_GRAPH_ID

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def _url(self, path: str) -> str:
        return f"{self.base_url}/graphs/{self.graph_id}{path}"

    def _handle(self, resp: requests.Response) -> Any:
        if resp.status_code >= 400:
            try:
                payload = resp.json()
            except ValueError:
                payload = {"error": resp.text}
            raise OmniGraphError(resp.status_code, payload)
        if resp.headers.get("content-type", "").startswith("application/x-ndjson"):
            return resp.text
        if not resp.content:
            return None
        return resp.json()

    # ---- stored queries -------------------------------------------------

    def invoke_query(
        self,
        name: str,
        params: dict[str, Any] | None = None,
        branch: str | None = None,
        snapshot: str | None = None,
        expect_mutation: bool | None = None,
    ) -> dict[str, Any]:
        body = {
            "params": params or {},
            "branch": branch,
            "snapshot": snapshot,
            "expect_mutation": expect_mutation,
        }
        resp = requests.post(
            self._url(f"/queries/{name}"), headers=self._headers(), json=body, timeout=30
        )
        return self._handle(resp)

    def list_queries(self) -> list[dict[str, Any]]:
        resp = requests.get(self._url("/queries"), headers=self._headers(), timeout=30)
        data = self._handle(resp)
        return data.get("queries", data) if isinstance(data, dict) else data

    def ad_hoc_query(self, gq_source: str, params: dict[str, Any] | None = None,
                      branch: str | None = None) -> dict[str, Any]:
        body = {"query": gq_source, "params": params or {}, "branch": branch}
        resp = requests.post(self._url("/query"), headers=self._headers(), json=body, timeout=30)
        return self._handle(resp)

    # ---- branches ---------------------------------------------------------

    def branch_list(self) -> list[dict[str, Any]]:
        resp = requests.get(self._url("/branches"), headers=self._headers(), timeout=30)
        data = self._handle(resp)
        return data.get("branches", data) if isinstance(data, dict) else data

    def branch_create(self, name: str, from_branch: str = "main") -> dict[str, Any]:
        body = {"name": name, "from": from_branch}
        resp = requests.post(self._url("/branches"), headers=self._headers(), json=body, timeout=30)
        return self._handle(resp)

    def branch_merge(self, source: str, target: str = "main") -> dict[str, Any]:
        body = {"source": source, "target": target}
        resp = requests.post(self._url("/branches/merge"), headers=self._headers(), json=body, timeout=30)
        return self._handle(resp)

    def branch_delete(self, name: str) -> None:
        # Branch names contain "/" (e.g. "ingest/<run-id>"), which must be
        # percent-encoded or the server's router sees extra path segments
        # and 404s instead of matching DELETE /branches/{branch}.
        resp = requests.delete(
            self._url(f"/branches/{quote(name, safe='')}"), headers=self._headers(), timeout=30
        )
        return self._handle(resp)

    # ---- bulk load ----------------------------------------------------

    def load(
        self,
        records: Iterable[dict[str, Any]],
        branch: str,
        from_branch: str | None = None,
        mode: str = "merge",
    ) -> dict[str, Any]:
        ndjson = "\n".join(json.dumps(r) for r in records)
        body = {"data": ndjson, "branch": branch, "from": from_branch, "mode": mode}
        resp = requests.post(self._url("/load"), headers=self._headers(), json=body, timeout=60)
        return self._handle(resp)

    # ---- commits / export -----------------------------------------------

    def commits(self, branch: str | None = None) -> list[dict[str, Any]]:
        params = {"branch": branch} if branch else {}
        resp = requests.get(self._url("/commits"), headers=self._headers(), params=params, timeout=30)
        data = self._handle(resp)
        return data.get("commits", data) if isinstance(data, dict) else data

    def export(self, branch: str = "main", type_names: list[str] | None = None) -> list[dict[str, Any]]:
        body = {"branch": branch, "type_names": type_names or [], "table_keys": []}
        resp = requests.post(self._url("/export"), headers=self._headers(), json=body, timeout=60)
        text = self._handle(resp)
        return [json.loads(line) for line in text.splitlines() if line.strip()]

    def snapshot(self, branch: str = "main") -> dict[str, Any]:
        resp = requests.get(self._url("/snapshot"), headers=self._headers(), params={"branch": branch}, timeout=30)
        return self._handle(resp)


# ---- dev-mode actor -> bearer token map ---------------------------------
# In this POC, tokens are opaque strings the dev server is configured with
# via cluster/tokens.dev.json (the same file omnigraph-server itself reads
# through OMNIGRAPH_SERVER_BEARER_TOKENS_FILE). Loaded from that one file
# rather than a second hardcoded copy here -- a hardcoded duplicate is
# exactly how "act-reviewer-nehal"/"act-reviewer-santosh" ended up missing
# and 500ing every approve/reject the first time this was added, even
# though the actual server-side tokens file, Cedar policy, and login
# accounts were all updated correctly. Real deployments would issue/rotate
# these through a secrets manager, not a checked-in JSON file at all.

_TOKENS_FILE = os.environ.get(
    "OMNIGRAPH_CLIENT_TOKENS_FILE",
    str(Path(__file__).resolve().parent.parent / "cluster" / "tokens.dev.json"),
)


def _load_actor_tokens() -> dict[str, str]:
    with open(_TOKENS_FILE, encoding="utf-8") as f:
        return json.load(f)


def client_for(actor: str, **kwargs: Any) -> OmniGraphClient:
    tokens = _load_actor_tokens()
    if actor not in tokens:
        raise KeyError(f"unknown actor '{actor}'; known: {sorted(tokens)} (from {_TOKENS_FILE})")
    return OmniGraphClient(token=tokens[actor], **kwargs)
