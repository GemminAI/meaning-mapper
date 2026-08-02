# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""RFC-SA002 verification matrix."""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

from meaning_mapper import AnnotatedObservation, AnnotationView, map_annotation
from meaning_mapper.runtime_bridge import RuntimeAnnotationDTO, StandardRuntimeBridge

SRC = Path(__file__).resolve().parents[1] / "src" / "meaning_mapper"
DOMAIN_PACKAGES = ("abi", "mapper", "payload", "engine")


def test_annotation_view_frozen() -> None:
    view = AnnotationView(annotation_id="a1", semantic_density=0.5)
    try:
        view.annotation_id = "mutated"  # type: ignore[misc]
        raised = False
    except (AttributeError, TypeError, dataclasses.FrozenInstanceError):
        raised = True
    assert raised


def test_dto_confinement_ast() -> None:
    """RuntimeAnnotationDTO only referenced from runtime_bridge.py."""
    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        if path.name == "runtime_bridge.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == "RuntimeAnnotationDTO":
                offenders.append(f"{path.name}:Name")
            if isinstance(node, ast.Attribute) and node.attr == "RuntimeAnnotationDTO":
                offenders.append(f"{path.name}:Attr")
    assert offenders == []


def test_boundary_purity_ast() -> None:
    """Domain packages must not import httpx/requests."""
    banned = {"httpx", "requests"}
    offenders: list[str] = []
    for pkg in DOMAIN_PACKAGES:
        root = SRC / pkg
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] in banned:
                            offenders.append(f"{path}:import {alias.name}")
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and node.module.split(".")[0] in banned
                ):
                    offenders.append(f"{path}:from {node.module}")
    assert offenders == []


def test_defensive_isolation() -> None:
    dto = RuntimeAnnotationDTO(
        annotation_id="x",
        payload_snapshot={
            "schema_id": "urn:gemminai:schema:sa003:1.0",
            "payload_class": "evaluative",
            "generator_signature": "test",
            "confidence": 0.9,
        },
        semantic_density=0.9,
    )
    view = StandardRuntimeBridge().bridge_annotation(dto)
    dto.payload_snapshot["confidence"] = 0.1
    dto.payload_snapshot["injected"] = True
    assert view.payload_snapshot.get("confidence") == 0.9
    assert "injected" not in view.payload_snapshot


def test_ignore_unknowns() -> None:
    raw = {
        "version": "1.0",
        "annotation_id": "a",
        "source_type": "t",
        "coordinates": [1, 2],
        "semantic_density": 0.5,
        "future_unsupported_field": {"x": 1},
        "payload_snapshot": {
            "schema_id": "urn:gemminai:schema:sa003:1.0",
            "payload_class": "categorical",
            "generator_signature": "test",
            "text_label": "ok",
            "future_dimension_tag": 99,
        },
    }
    view = StandardRuntimeBridge().bridge_annotation(raw)
    assert view.annotation_id == "a"
    assert view.payload_snapshot.get("text_label") == "ok"
    assert "future_dimension_tag" not in view.payload_snapshot
    assert not hasattr(view, "future_unsupported_field")


def test_mapper_no_second_copy_identity() -> None:
    view = AnnotationView(annotation_id="id", payload_snapshot={"schema_id": "urn:gemminai:schema:sa003:1.0"})
    annotated = map_annotation("prompt_1", view, observation_id="obs_1")
    assert isinstance(annotated, AnnotatedObservation)
    assert annotated.view is view
