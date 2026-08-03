"""Structural types crossing Meaning Mapper's boundaries.

Meaning Mapper does not import semantic-annotator-core or msr: both
crossings are structural (duck-typed), matching the ecosystem's port
convention (see RFC-MSR01 Section 4 -- "any object satisfying a port's
shape MAY be bound"). ``HEXTObservation`` below documents the subset of the
HEXT JSON transport shape Meaning Mapper actually reads; it does not claim
to be the full HEXT schema.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from meaning_mapper._linalg import FloatArray

HEXTObservation = Mapping[str, Any]
"""A HEXT Observation Object as produced upstream by semantic-annotator-core."""


@dataclass(frozen=True, slots=True)
class ValidatedObservation:
    """The typed, checked subset of a HEXT Observation the pipeline operates on."""

    observation_id: str
    text: str
    metadata: dict[str, Any]
    content_hash: str
    timestamp_ns: int
    raw_features: FloatArray = field(repr=False, compare=False)
    provenance: tuple[str, ...] = field(default_factory=tuple)
