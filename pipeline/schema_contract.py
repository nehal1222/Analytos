"""Pydantic contract for the LLM extraction step.

Field names and enums here are chosen to map 1:1 onto poc/cluster/knowledge.pg
so `build_graph.py` can turn this straight into typed node/edge records. The
LLM (or the mock extractor) never invents `slug`/`id` values -- those are
always derived deterministically downstream in `slugs.py`, which is what
makes re-ingesting the same document idempotent regardless of any
run-to-run non-determinism in the LLM's phrasing.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MetricType = Literal["percentage", "ratio", "duration", "count", "currency"]
RoleLevel = Literal["economic_buyer", "champion", "user"]
DecisionStatus = Literal["proposed", "approved", "implemented"]


class ExtractedProduct(BaseModel):
    name: str
    category: str | None = None
    summary: str | None = None


class ExtractedFeature(BaseModel):
    product_name: str
    name: str
    description: str | None = None


class ExtractedProofPoint(BaseModel):
    product_name: str
    feature_name: str | None = None  # set only if this proof point is feature-specific
    label: str
    value: str
    metric_type: MetricType
    baseline: str | None = None
    description: str | None = None


class ExtractedDecision(BaseModel):
    product_name: str | None = None
    title: str
    description: str | None = None
    status: DecisionStatus = "approved"
    decided_at: str | None = None  # ISO date, e.g. "2026-04-02"
    decided_by_person_names: list[str] = Field(default_factory=list)
    discussed_in_thread_ids: list[str] = Field(default_factory=list)


class ExtractedICPSegment(BaseModel):
    name: str
    firmographics: str | None = None
    tech_signals: str | None = None
    trigger_signals: str | None = None
    competitor_angle: str | None = None
    targets_product_names: list[str] = Field(default_factory=list)


class ExtractedPersona(BaseModel):
    title: str
    role_level: RoleLevel
    description: str | None = None
    segment_names: list[str] = Field(default_factory=list)


class ExtractedPerson(BaseModel):
    name: str
    email: str | None = None
    company: str | None = None
    role: str | None = None


class ExtractedEmailThread(BaseModel):
    thread_id: str
    subject: str
    summary: str | None = None
    occurred_at: str | None = None  # ISO date of the last message in the thread
    participant_names: list[str] = Field(default_factory=list)
    about_product_names: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    products: list[ExtractedProduct] = Field(default_factory=list)
    features: list[ExtractedFeature] = Field(default_factory=list)
    proof_points: list[ExtractedProofPoint] = Field(default_factory=list)
    decisions: list[ExtractedDecision] = Field(default_factory=list)
    icp_segments: list[ExtractedICPSegment] = Field(default_factory=list)
    personas: list[ExtractedPersona] = Field(default_factory=list)
    people: list[ExtractedPerson] = Field(default_factory=list)
    email_threads: list[ExtractedEmailThread] = Field(default_factory=list)
