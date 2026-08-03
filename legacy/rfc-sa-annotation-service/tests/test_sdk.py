# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

from meaning_mapper import (
    AnnotatedObservation,
    AnnotationView,
    __version__,
    map_annotation,
)
from meaning_mapper.engine import DeterministicAnnotatorEngine
from meaning_mapper.runtime_bridge import StandardRuntimeBridge


def test_version() -> None:
    assert __version__ == "1.0.0"


def test_public_exports() -> None:
    view = AnnotationView(annotation_id="a")
    annotated = map_annotation("p", view, observation_id="o")
    assert isinstance(annotated, AnnotatedObservation)


def test_engine_deterministic() -> None:
    engine = DeterministicAnnotatorEngine()
    a = engine.annotate(
        observation_id="obs",
        prompt_id="prompt",
        raw_observational_data={"acceleration": [1.0, 2.0, 3.0]},
    )
    b = engine.annotate(
        observation_id="obs",
        prompt_id="prompt",
        raw_observational_data={"acceleration": [1.0, 2.0, 3.0]},
    )
    assert a == b
    view = StandardRuntimeBridge().bridge_annotation(a)
    assert view.coordinates == (1.0, 2.0, 3.0)
