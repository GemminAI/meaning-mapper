# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""Model-independent deterministic annotator (RFC-SA001 Principles 1–4).

Uses structural signals only. Optionally consults semantic-annotator-core for
HEXT metadata metrics — never LLMs, never commercial runtime control.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from meaning_mapper.payload.schema import SCHEMA_ID, clamp_density, compute_semantic_density
from meaning_mapper.version import __version__


def _stable_id(observation_id: str, prompt_id: str, raw: dict[str, Any]) -> str:
    digest = hashlib.sha256(
        json.dumps(
            {"o": observation_id, "p": prompt_id, "r": raw},
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"annot_{digest}"


def _extract_coordinates(raw: dict[str, Any]) -> list[float]:
    for key in ("coordinates", "acceleration", "embedding", "vector"):
        value = raw.get(key)
        if isinstance(value, (list, tuple)) and value:
            try:
                return [float(x) for x in value]
            except (TypeError, ValueError):
                continue
    return []


def _core_metrics(raw: dict[str, Any]) -> dict[str, Any]:
    """Best-effort structural metrics from semantic-annotator-core (optional)."""
    try:
        from semantic_annotator.pipeline import annotate
    except ImportError:
        return {}
    try:
        obj = annotate(raw, source_type="json")
        metrics = obj.get("object", {}).get("metrics") or {}
        return dict(metrics) if isinstance(metrics, dict) else {}
    except Exception:  # noqa: BLE001 — Core is optional; any failure yields no metrics
        return {}


class DeterministicAnnotatorEngine:
    """Descriptive, reproducible, replaceable annotator — no model inference."""

    generator_signature = f"meaning-mapper-deterministic-v{__version__}"

    def annotate(
        self,
        *,
        observation_id: str,
        prompt_id: str,
        raw_observational_data: dict[str, Any],
        client_id: str = "",
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        raw = dict(raw_observational_data or {})
        coords = _extract_coordinates(raw)
        metrics = _core_metrics(raw)

        # Descriptive labels from observation keys / prompt — not predictive.
        text_label = str(raw.get("text_label") or raw.get("state") or "observed")
        semantic_class = str(
            raw.get("semantic_class") or prompt_id or "unclassified_observation"
        )
        is_anomaly = bool(raw.get("is_anomaly", False))

        token_est = float(metrics.get("tokens_estimated") or len(json.dumps(raw, default=str)))
        # Bounded structural confidence from payload richness (deterministic).
        confidence = clamp_density(min(1.0, 0.55 + min(token_est, 40.0) / 100.0))
        drift_index = clamp_density(float(raw.get("drift_index", 0.0) or 0.0))
        density = compute_semantic_density(confidence, entropy=drift_index)

        annotation_id = _stable_id(observation_id, prompt_id, raw)

        payload_snapshot: dict[str, Any] = {
            "schema_id": SCHEMA_ID,
            "payload_class": "hybrid",
            "generator_signature": self.generator_signature,
            "text_label": text_label,
            "semantic_class": semantic_class,
            "ontology_uri": str(
                raw.get("ontology_uri")
                or "https://gemminai.com/ontology/v1/states#observed"
            ),
            "is_anomaly": is_anomaly,
            "confidence": confidence,
            "drift_index": drift_index,
            "semantic_density": density,
        }
        if coords:
            payload_snapshot["coordinates"] = coords
        if client_id:
            payload_snapshot["client_id"] = client_id  # will be ignored by SA003 filter
        if timestamp:
            payload_snapshot["timestamp"] = timestamp  # ignored by SA003 filter

        return {
            "schema_id": SCHEMA_ID,
            "version": "1.0",
            "annotation_id": annotation_id,
            "source_type": "deterministic_descriptive",
            "coordinates": coords,
            "semantic_density": density,
            "payload_snapshot": payload_snapshot,
        }
