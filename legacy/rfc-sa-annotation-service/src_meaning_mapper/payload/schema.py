# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""RFC-SA003 Annotation Payload Schema — vocabulary and normalization."""

from __future__ import annotations

from copy import deepcopy
from enum import Enum
from typing import Any

SCHEMA_ID = "urn:gemminai:schema:sa003:1.0"

# Known SA003 data keys (unknowns are ignored).
CATEGORICAL_KEYS = frozenset(
    {
        "text_label",
        "semantic_class",
        "ontology_uri",
        "alternative_labels",
        "is_anomaly",
    }
)
SPATIAL_KEYS = frozenset(
    {
        "target_roi",
        "bounding_box",
        "coordinates",
        "time_segment",
    }
)
EVALUATIVE_KEYS = frozenset(
    {
        "confidence",
        "semantic_density",
        "drift_index",
        "entropy_reduction",
    }
)
KNOWN_DATA_KEYS = CATEGORICAL_KEYS | SPATIAL_KEYS | EVALUATIVE_KEYS

DEFAULT_CONFIDENCE = 1.0
DEFAULT_DRIFT_INDEX = 0.0
DEFAULT_SEMANTIC_DENSITY = 0.0


class PayloadClass(str, Enum):
    CATEGORICAL = "categorical"
    SPATIAL = "spatial"
    EVALUATIVE = "evaluative"
    HYBRID = "hybrid"


class SchemaValidationError(ValueError):
    """Raised when schema_id is missing or not SA003-compatible."""


def validate_schema_id(schema_id: Any) -> str:
    if not isinstance(schema_id, str) or not schema_id.startswith(
        "urn:gemminai:schema:sa003:"
    ):
        raise SchemaValidationError(
            f"unsupported schema_id: {schema_id!r}; expected {SCHEMA_ID}"
        )
    # Accept exact 1.0 or forward-compatible sa003 minor updates under same URN family.
    return schema_id


def clamp_density(value: float) -> float:
    """RFC-SA003: clamp semantic_density to [0, 1]."""
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def compute_semantic_density(
    confidence: float,
    entropy: float = 0.0,
    entropy_max: float = 1.0,
) -> float:
    """RFC-SA003 §4.1: D_s = c * (1 - H_annot / H_max), clamped to [0, 1]."""
    try:
        c = float(confidence)
    except (TypeError, ValueError):
        c = DEFAULT_CONFIDENCE
    c = clamp_density(c)
    try:
        h = float(entropy)
        h_max = float(entropy_max) if float(entropy_max) != 0.0 else 1.0
    except (TypeError, ValueError):
        return clamp_density(c)
    density = c * (1.0 - (h / h_max))
    return clamp_density(density)


def _coerce_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _filter_known(data: dict[str, Any]) -> dict[str, Any]:
    """Ignore unknowns (RFC-SA003 Ignore Unknowns)."""
    return {k: deepcopy(v) for k, v in data.items() if k in KNOWN_DATA_KEYS}


def normalize_payload(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize a SA003 payload header + data block.

    Required headers: schema_id, payload_class, generator_signature.
    Unknown data keys are dropped. Missing evaluative fields get neutral defaults.
    """
    if not isinstance(raw, dict):
        raise SchemaValidationError("payload must be an object")

    schema_id = validate_schema_id(raw.get("schema_id", SCHEMA_ID))

    payload_class = str(raw.get("payload_class", "hybrid"))
    valid_classes = {c.value for c in PayloadClass}
    if payload_class not in valid_classes:
        payload_class = PayloadClass.HYBRID.value

    generator_signature = str(raw.get("generator_signature", "")).strip()
    if not generator_signature:
        raise SchemaValidationError("generator_signature is required")

    data_in = raw.get("data")
    if data_in is None and any(k in raw for k in KNOWN_DATA_KEYS):
        # Flat SA005 payload_snapshot style: vocab keys at top level.
        data_in = {k: raw[k] for k in KNOWN_DATA_KEYS if k in raw}
    if not isinstance(data_in, dict):
        data_in = {}

    data = _filter_known(data_in)

    # Nullable defaults (RFC-SA003 §5.2)
    if "confidence" in data or payload_class in {
        PayloadClass.EVALUATIVE.value,
        PayloadClass.HYBRID.value,
    }:
        data["confidence"] = _coerce_float(
            data.get("confidence", DEFAULT_CONFIDENCE), DEFAULT_CONFIDENCE
        )
        data["confidence"] = clamp_density(data["confidence"])
    if "drift_index" in data or payload_class in {
        PayloadClass.EVALUATIVE.value,
        PayloadClass.HYBRID.value,
    }:
        data["drift_index"] = _coerce_float(
            data.get("drift_index", DEFAULT_DRIFT_INDEX), DEFAULT_DRIFT_INDEX
        )
    if "semantic_density" in data:
        data["semantic_density"] = clamp_density(
            _coerce_float(data.get("semantic_density"), DEFAULT_SEMANTIC_DENSITY)
        )

    return {
        "schema_id": schema_id,
        "payload_class": payload_class,
        "generator_signature": generator_signature,
        "data": data,
    }
