"""Deterministic slug/id derivation.

Idempotent re-ingestion depends entirely on this module producing the same
slug for the same natural-language key every time, independent of any
LLM run-to-run variance. The extractor is instructed to copy names/labels
verbatim from source text; slugs are always computed here, never trusted
from the LLM.
"""

from __future__ import annotations

import re


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def product_slug(name: str) -> str:
    return f"product--{slugify(name)}"


def feature_slug(product_name: str, feature_name: str) -> str:
    return f"feature--{slugify(product_name)}--{slugify(feature_name)}"


def proof_point_slug(product_name: str, label: str, feature_name: str | None = None) -> str:
    if feature_name:
        return f"pp--{slugify(product_name)}--{slugify(feature_name)}--{slugify(label)}"
    return f"pp--{slugify(product_name)}--{slugify(label)}"


def decision_slug(title: str, product_name: str | None = None) -> str:
    if product_name:
        return f"decision--{slugify(product_name)}--{slugify(title)}"
    return f"decision--{slugify(title)}"


def icp_segment_slug(name: str) -> str:
    return f"segment--{slugify(name)}"


def persona_slug(title: str) -> str:
    return f"persona--{slugify(title)}"


def person_slug(name: str, email: str | None = None) -> str:
    if email:
        return f"person--{slugify(email)}"
    return f"person--{slugify(name)}"


def email_thread_slug(thread_id: str) -> str:
    return f"thread--{slugify(thread_id)}"
