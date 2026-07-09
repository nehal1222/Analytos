"""Resolve one or more ExtractionResults into a single, idempotent set of
NDJSON node/edge records ready for `omnigraph load --mode merge`.

Cross-document references (an email thread mentioning "Stockly", a persona
naming its ICP segment) are resolved by natural key against everything
extracted so far in this run. An edge whose endpoint can't be resolved is
dropped with a warning rather than failing the whole load -- see
`poc/README.md` for why (referential integrity would otherwise make the
pipeline fragile to extraction order or partial LLM recall).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import slugs
from schema_contract import ExtractionResult


@dataclass
class BuildResult:
    records: list[dict]
    warnings: list[str] = field(default_factory=list)
    node_counts: dict[str, int] = field(default_factory=dict)
    edge_counts: dict[str, int] = field(default_factory=dict)


def build(results: list[tuple[str, ExtractionResult]], ingest_run: str) -> BuildResult:
    records: list[dict] = []
    warnings: list[str] = []
    node_counts: dict[str, int] = {}
    edge_counts: dict[str, int] = {}

    product_by_name: dict[str, str] = {}
    feature_by_key: dict[tuple[str, str], str] = {}
    segment_by_name: dict[str, str] = {}
    person_by_name: dict[str, str] = {}
    thread_by_id: dict[str, str] = {}

    # A single `load` call can't contain two rows with the same @key (the
    # engine rejects it as a @unique violation, not a silent last-write-wins)
    # -- so the same entity mentioned in two source docs within one run
    # (e.g. a person on two email threads) must be deduped here. Cross-run
    # idempotency is separately handled by `load --mode merge` upserting
    # against main.
    seen_nodes: set[tuple[str, str]] = set()
    seen_edges: set[tuple[str, str, str]] = set()

    def add_node(node_type: str, data: dict) -> None:
        key = (node_type, data["slug"])
        if key in seen_nodes:
            return
        seen_nodes.add(key)
        clean = {k: v for k, v in data.items() if v is not None}
        records.append({"type": node_type, "data": clean})
        node_counts[node_type] = node_counts.get(node_type, 0) + 1

    def add_edge(edge_type: str, src: str | None, dst: str | None, ctx: str) -> None:
        if not src or not dst:
            warnings.append(f"skipped {edge_type} edge ({ctx}): unresolved endpoint")
            return
        key = (edge_type, src, dst)
        if key in seen_edges:
            return
        seen_edges.add(key)
        records.append({"edge": edge_type, "from": src, "to": dst, "data": {}})
        edge_counts[edge_type] = edge_counts.get(edge_type, 0) + 1

    # Pass 1: register every product across all docs first, so a reference
    # to a product defined in a different document (e.g. an email thread
    # naming "Stockly") always resolves regardless of doc order.
    for source_doc, res in results:
        for p in res.products:
            slug = slugs.product_slug(p.name)
            product_by_name.setdefault(p.name.lower(), slug)
            add_node(
                "Product",
                {
                    "slug": slug,
                    "name": p.name,
                    "category": p.category,
                    "summary": p.summary,
                    "source_doc": source_doc,
                    "ingest_run": ingest_run,
                },
            )

    # Pass 2: everything else.
    for source_doc, res in results:
        for f in res.features:
            prod_slug = product_by_name.get(f.product_name.lower())
            if not prod_slug:
                warnings.append(f"skipped Feature '{f.name}': unknown product '{f.product_name}'")
                continue
            fslug = slugs.feature_slug(f.product_name, f.name)
            feature_by_key[(prod_slug, f.name.lower())] = fslug
            add_node(
                "Feature",
                {
                    "slug": fslug,
                    "name": f.name,
                    "description": f.description,
                    "source_doc": source_doc,
                    "ingest_run": ingest_run,
                },
            )
            add_edge("HasFeature", prod_slug, fslug, f"{f.product_name}->{f.name}")

        for pp in res.proof_points:
            prod_slug = product_by_name.get(pp.product_name.lower())
            if not prod_slug:
                warnings.append(f"skipped ProofPoint '{pp.label}': unknown product '{pp.product_name}'")
                continue
            ppslug = slugs.proof_point_slug(pp.product_name, pp.label, pp.feature_name)
            add_node(
                "ProofPoint",
                {
                    "slug": ppslug,
                    "label": pp.label,
                    "value": pp.value,
                    "metric_type": pp.metric_type,
                    "baseline": pp.baseline,
                    "description": pp.description,
                    "source_doc": source_doc,
                    "ingest_run": ingest_run,
                },
            )
            if pp.feature_name:
                fslug = feature_by_key.get((prod_slug, pp.feature_name.lower()))
                add_edge("FeatureProvenBy", fslug, ppslug, f"{pp.feature_name}->{pp.label}")
            else:
                add_edge("ProvenBy", prod_slug, ppslug, f"{pp.product_name}->{pp.label}")

        for s in res.icp_segments:
            sslug = slugs.icp_segment_slug(s.name)
            segment_by_name.setdefault(s.name.lower(), sslug)
            add_node(
                "ICPSegment",
                {
                    "slug": sslug,
                    "name": s.name,
                    "firmographics": s.firmographics,
                    "tech_signals": s.tech_signals,
                    "trigger_signals": s.trigger_signals,
                    "competitor_angle": s.competitor_angle,
                    "source_doc": source_doc,
                    "ingest_run": ingest_run,
                },
            )
            for pname in s.targets_product_names:
                add_edge("Targets", product_by_name.get(pname.lower()), sslug, f"{pname}->{s.name}")

        for per in res.personas:
            perslug = slugs.persona_slug(per.title)
            add_node(
                "Persona",
                {
                    "slug": perslug,
                    "title": per.title,
                    "role_level": per.role_level,
                    "description": per.description,
                    "source_doc": source_doc,
                    "ingest_run": ingest_run,
                },
            )
            for sname in per.segment_names:
                add_edge(
                    "SegmentPersona", segment_by_name.get(sname.lower()), perslug, f"{sname}->{per.title}"
                )

        for person in res.people:
            pslug = slugs.person_slug(person.name, person.email)
            person_by_name.setdefault(person.name.lower(), pslug)
            add_node(
                "Person",
                {
                    "slug": pslug,
                    "name": person.name,
                    "email": person.email,
                    "company": person.company,
                    "role": person.role,
                    "source_doc": source_doc,
                    "ingest_run": ingest_run,
                },
            )

        for t in res.email_threads:
            tslug = slugs.email_thread_slug(t.thread_id)
            thread_by_id.setdefault(t.thread_id.lower(), tslug)
            add_node(
                "EmailThread",
                {
                    "slug": tslug,
                    "thread_id": t.thread_id,
                    "subject": t.subject,
                    "summary": t.summary,
                    "internal_only": True,
                    "occurred_at": t.occurred_at,
                    "source_doc": source_doc,
                    "ingest_run": ingest_run,
                },
            )
            for pname in t.about_product_names:
                add_edge(
                    "ThreadAbout", tslug, product_by_name.get(pname.lower()), f"{t.thread_id}->{pname}"
                )
            for pname in t.participant_names:
                add_edge(
                    "ParticipatedIn",
                    person_by_name.get(pname.lower()),
                    tslug,
                    f"{pname}->{t.thread_id}",
                )

        for d in res.decisions:
            dslug = slugs.decision_slug(d.title, d.product_name)
            add_node(
                "Decision",
                {
                    "slug": dslug,
                    "title": d.title,
                    "description": d.description,
                    "status": d.status,
                    "decided_at": d.decided_at,
                    "source_doc": source_doc,
                    "ingest_run": ingest_run,
                },
            )
            if d.product_name:
                add_edge(
                    "DecisionAbout",
                    dslug,
                    product_by_name.get(d.product_name.lower()),
                    f"{d.title}->{d.product_name}",
                )
            for pname in d.decided_by_person_names:
                add_edge(
                    "DecidedBy", dslug, person_by_name.get(pname.lower()), f"{d.title}->{pname}"
                )
            for tid in d.discussed_in_thread_ids:
                add_edge(
                    "DecisionDiscussedIn",
                    dslug,
                    thread_by_id.get(tid.lower()),
                    f"{d.title}->{tid}",
                )

    return BuildResult(
        records=records, warnings=warnings, node_counts=node_counts, edge_counts=edge_counts
    )
