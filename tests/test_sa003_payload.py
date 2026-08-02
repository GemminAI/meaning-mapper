# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""RFC-SA003 verification matrix."""

from __future__ import annotations

import pytest

from meaning_mapper.payload.schema import (
    SCHEMA_ID,
    SchemaValidationError,
    clamp_density,
    compute_semantic_density,
    normalize_payload,
)


def test_sa003_schema_id_validation() -> None:
    with pytest.raises(SchemaValidationError):
        normalize_payload(
            {
                "schema_id": "urn:evil:1.0",
                "payload_class": "categorical",
                "generator_signature": "x",
                "data": {},
            }
        )


def test_sa003_ignore_unknowns() -> None:
    out = normalize_payload(
        {
            "schema_id": SCHEMA_ID,
            "payload_class": "categorical",
            "generator_signature": "test",
            "data": {
                "text_label": "Normal Operating State",
                "future_dimension_tag": "nope",
            },
        }
    )
    assert out["data"]["text_label"] == "Normal Operating State"
    assert "future_dimension_tag" not in out["data"]


def test_sa003_density_clamping() -> None:
    assert clamp_density(1.25) == 1.0
    assert clamp_density(-0.5) == 0.0
    assert compute_semantic_density(1.0, entropy=0.0) == 1.0
    assert compute_semantic_density(0.5, entropy=0.0) == 0.5
    # Over-range via negative entropy contribution still clamps
    assert compute_semantic_density(2.0, entropy=-1.0) == 1.0


def test_nullable_defaults() -> None:
    out = normalize_payload(
        {
            "schema_id": SCHEMA_ID,
            "payload_class": "evaluative",
            "generator_signature": "verifier",
            "data": {},
        }
    )
    assert out["data"]["confidence"] == 1.0
    assert out["data"]["drift_index"] == 0.0
