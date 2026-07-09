"""Edge endpoint types + existence checks, shared by the ingestion pipeline
(to skip re-asserting an edge that already exists, see ingest.py) and the
console's HITL diff (diff.py).

Why this is needed: `load --mode merge` upserts NODE rows by their declared
`@key`, but edge rows have no user-visible key (just an internal id) --
re-submitting an edge that already exists on the target branch creates a
genuinely new row, which then collides with the edge's `@unique(src, dst)`
constraint instead of silently no-op'ing. So idempotent re-ingestion has to
check for an edge's existence explicitly rather than relying on merge mode
alone (unlike nodes, where merge mode is sufficient).
"""

from __future__ import annotations

EDGE_ENDPOINTS: dict[str, tuple[str, str]] = {
    "HasFeature": ("Product", "Feature"),
    "ProvenBy": ("Product", "ProofPoint"),
    "FeatureProvenBy": ("Feature", "ProofPoint"),
    "Targets": ("Product", "ICPSegment"),
    "SegmentPersona": ("ICPSegment", "Persona"),
    "ParticipatedIn": ("Person", "EmailThread"),
    "ThreadAbout": ("EmailThread", "Product"),
    "DiscussedIn": ("ProofPoint", "EmailThread"),
    "DecisionDiscussedIn": ("Decision", "EmailThread"),
    "DecidedBy": ("Decision", "Person"),
    "DecisionAbout": ("Decision", "Product"),
}


def edge_ident(edge_type: str) -> str:
    # .gq traversal syntax requires a lowercase-leading edge identifier
    # (pest rule `edge_ident`); schema-declared edge type names stay
    # PascalCase (e.g. "HasFeature") and match case-insensitively, so
    # lowercasing just the first letter here is enough.
    return edge_type[:1].lower() + edge_type[1:]


def edge_exists(client, edge_type: str, src: str, dst: str, branch: str) -> bool:
    src_type, dst_type = EDGE_ENDPOINTS[edge_type]
    source = (
        f"query check_edge($src: String, $dst: String) {{ "
        f"match {{ "
        f"$a: {src_type} {{ slug: $src }} "
        f"$b: {dst_type} {{ slug: $dst }} "
        f"$a {edge_ident(edge_type)} $b "
        f"}} return {{ $a.slug as slug }} }}"
    )
    result = client.ad_hoc_query(source, {"src": src, "dst": dst}, branch=branch)
    return (result.get("row_count") or 0) > 0
