# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""RFC-SA004 verification matrix."""

from __future__ import annotations

import json
from pathlib import Path

from meaning_mapper.runtime_bridge import (
    ReplayRuntimeBridge,
    RuntimeAnnotationDTO,
    StandardRuntimeBridge,
)


def test_dto_isolation() -> None:
    payload = {
        "schema_id": "urn:gemminai:schema:sa003:1.0",
        "payload_class": "spatial",
        "generator_signature": "t",
        "confidence": 0.8,
        "bounding_box": {"x_min": 1.0, "y_min": 2.0, "x_max": 3.0, "y_max": 4.0},
    }
    dto = RuntimeAnnotationDTO(payload_snapshot=payload, semantic_density=0.8)
    view = StandardRuntimeBridge().bridge_annotation(dto)
    dto.payload_snapshot["confidence"] = 0.0
    dto.payload_snapshot["bounding_box"]["x_min"] = 99.0
    assert view.payload_snapshot["confidence"] == 0.8
    assert view.payload_snapshot["bounding_box"]["x_min"] == 1.0


def test_ignore_extra_fields() -> None:
    class Weird:
        def __init__(self) -> None:
            self.version = "1.0"
            self.annotation_id = "x"
            self.source_type = "s"
            self.coordinates = [0.1, 0.2]
            self.semantic_density = 0.3
            self.payload_snapshot = {
                "schema_id": "urn:gemminai:schema:sa003:1.0",
                "payload_class": "spatial",
                "generator_signature": "yolo",
                "coordinates": [0.1, 0.2],
            }
            self.future_extension_tag = "hello"

    view = StandardRuntimeBridge().bridge_annotation(Weird())
    assert view.annotation_id == "x"
    assert view.coordinates == (0.1, 0.2)


def test_density_clamping() -> None:
    bridge = StandardRuntimeBridge()
    hi = bridge.bridge_annotation(
        RuntimeAnnotationDTO(semantic_density=1.25, payload_snapshot={})
    )
    lo = bridge.bridge_annotation(
        RuntimeAnnotationDTO(semantic_density=-0.5, payload_snapshot={})
    )
    # empty payload → view keeps clamped top-level density
    assert hi.semantic_density == 1.0
    assert lo.semantic_density == 0.0


def test_string_density_coercion() -> None:
    view = StandardRuntimeBridge().bridge_annotation(
        RuntimeAnnotationDTO(semantic_density="0.85", payload_snapshot={})
    )
    assert view.semantic_density == 0.85


def test_replay_bridge(tmp_path: Path) -> None:
    path = tmp_path / "annot.json"
    path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "annotation_id": "replay_1",
                "source_type": "file",
                "coordinates": [1.0],
                "semantic_density": 0.4,
                "payload_snapshot": {
                    "schema_id": "urn:gemminai:schema:sa003:1.0",
                    "payload_class": "hybrid",
                    "generator_signature": "replay",
                    "text_label": "from_file",
                },
            }
        ),
        encoding="utf-8",
    )
    view = ReplayRuntimeBridge(path).bridge_annotation()
    assert view.annotation_id == "replay_1"
    assert view.payload_snapshot["text_label"] == "from_file"


def test_bad_schema_dropped() -> None:
    view = StandardRuntimeBridge().bridge_annotation(
        {
            "annotation_id": "bad",
            "payload_snapshot": {
                "schema_id": "urn:nope",
                "payload_class": "categorical",
                "generator_signature": "x",
            },
        }
    )
    assert view.annotation_id == ""
    assert view.payload_snapshot == {}
