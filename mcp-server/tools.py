"""OmniGraph stored-query wrappers exposed as MCP tools.

Every function here is a thin, read-only wrapper around one stored `.gq`
query (see poc/cluster/queries/*.gq). `CLIENT` is set once at process
startup (see mcp_server.py) to a `GatewayClient` carrying this role's
gateway API key -- NOT a real omnigraph-server bearer token (see gateway.py
for why that distinction is the whole point). Every call here goes through
the query gateway, which independently allowlists query names per role and
never accepts anything but a pre-vetted named query against `main`.
"""

from __future__ import annotations

import os

import requests

GATEWAY_URL = os.environ.get("QUERY_GATEWAY_URL", "http://127.0.0.1:8090")


class GatewayClient:
    """Same `.invoke_query(name, params)["rows"]` shape as OmniGraphClient,
    so the tool functions below didn't need to change -- just what CLIENT
    actually talks to.
    """

    def __init__(self, api_key: str):
        self._api_key = api_key

    def invoke_query(self, name: str, params: dict | None = None) -> dict:
        resp = requests.post(
            f"{GATEWAY_URL}/invoke",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"query_name": name, "params": params or {}},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


CLIENT: GatewayClient | None = None


def list_products() -> list[dict]:
    """List every product in the approved knowledge graph (name, category, summary)."""
    return CLIENT.invoke_query("list_products")["rows"]


def get_product(product_slug: str) -> dict:
    """Get one product's summary by slug (see list_products for slugs)."""
    rows = CLIENT.invoke_query("get_product", {"slug": product_slug})["rows"]
    return rows[0] if rows else {}


def list_features_for_product(product_slug: str) -> list[dict]:
    """List the features of a product, by product slug."""
    return CLIENT.invoke_query("list_features_for_product", {"slug": product_slug})["rows"]


def list_all_features() -> list[dict]:
    """List every feature across all products."""
    return CLIENT.invoke_query("list_all_features")["rows"]


def list_proof_points_for_product(product_slug: str) -> list[dict]:
    """List product-level proof points / metrics for a product, by slug."""
    return CLIENT.invoke_query("list_proof_points_for_product", {"slug": product_slug})["rows"]


def list_proof_points_for_feature(feature_slug: str) -> list[dict]:
    """List proof points / metrics specific to one feature, by feature slug."""
    return CLIENT.invoke_query("list_proof_points_for_feature", {"slug": feature_slug})["rows"]


def list_all_proof_points() -> list[dict]:
    """List every proof point / metric in the graph, across all products."""
    return CLIENT.invoke_query("list_all_proof_points")["rows"]


def list_decisions_for_product(product_slug: str) -> list[dict]:
    """List recorded product decisions for a product, by slug."""
    return CLIENT.invoke_query("list_decisions_for_product", {"slug": product_slug})["rows"]


def list_decisions() -> list[dict]:
    """List every recorded decision in the graph, most recent first."""
    return CLIENT.invoke_query("list_decisions")["rows"]


def list_icp_segments() -> list[dict]:
    """List every ICP (ideal customer profile) segment."""
    return CLIENT.invoke_query("list_icp_segments")["rows"]


def get_icp_segment(segment_slug: str) -> dict:
    """Get one ICP segment's firmographics/trigger-signals/competitor-angle by slug."""
    rows = CLIENT.invoke_query("get_icp_segment", {"slug": segment_slug})["rows"]
    return rows[0] if rows else {}


def list_segments_for_product(product_slug: str) -> list[dict]:
    """List the ICP segments a given product targets, by product slug."""
    return CLIENT.invoke_query("list_segments_for_product", {"slug": product_slug})["rows"]


def list_personas() -> list[dict]:
    """List every buyer/champion persona in the graph."""
    return CLIENT.invoke_query("list_personas")["rows"]


def list_personas_for_segment(segment_slug: str) -> list[dict]:
    """List the personas targeted within one ICP segment, by segment slug."""
    return CLIENT.invoke_query("list_personas_for_segment", {"slug": segment_slug})["rows"]


def search_products(query_text: str) -> list[dict]:
    """Hybrid (vector + BM25, fused with RRF) search over products."""
    return CLIENT.invoke_query("search_products", {"q": query_text})["rows"]


def search_features(query_text: str) -> list[dict]:
    """Hybrid (vector + BM25, fused with RRF) search over features."""
    return CLIENT.invoke_query("search_features", {"q": query_text})["rows"]


def search_proof_points(query_text: str) -> list[dict]:
    """Hybrid (vector + BM25, fused with RRF) search over proof points / metrics."""
    return CLIENT.invoke_query("search_proof_points", {"q": query_text})["rows"]


def search_decisions(query_text: str) -> list[dict]:
    """Hybrid (vector + BM25, fused with RRF) search over decisions."""
    return CLIENT.invoke_query("search_decisions", {"q": query_text})["rows"]


def search_icp_segments(query_text: str) -> list[dict]:
    """Hybrid (vector + BM25, fused with RRF) search over ICP segments."""
    return CLIENT.invoke_query("search_icp_segments", {"q": query_text})["rows"]


TOOL_REGISTRY = {
    fn.__name__: fn
    for fn in [
        list_products,
        get_product,
        list_features_for_product,
        list_all_features,
        list_proof_points_for_product,
        list_proof_points_for_feature,
        list_all_proof_points,
        list_decisions_for_product,
        list_decisions,
        list_icp_segments,
        get_icp_segment,
        list_segments_for_product,
        list_personas,
        list_personas_for_segment,
        search_products,
        search_features,
        search_proof_points,
        search_decisions,
        search_icp_segments,
    ]
}
