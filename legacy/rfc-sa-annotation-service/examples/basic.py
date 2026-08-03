# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""Minimal Meaning Mapper SDK example (RFC-SA001–SA005)."""

from meaning_mapper import map_annotation
from meaning_mapper.engine import DeterministicAnnotatorEngine
from meaning_mapper.runtime_bridge import StandardRuntimeBridge

wire = DeterministicAnnotatorEngine().annotate(
    observation_id="obs_1",
    prompt_id="prompt_stability_analysis_v1",
    raw_observational_data={
        "acceleration": [0.01, -0.05, 9.81],
        "voltage": 12.45,
    },
)

view = StandardRuntimeBridge().bridge_annotation(wire)
annotated = map_annotation("prompt_stability_analysis_v1", view, observation_id="obs_1")
print(annotated.view.annotation_id)
print(annotated.view.semantic_density)
print(annotated.view.to_wire()["payload_snapshot"]["text_label"])
