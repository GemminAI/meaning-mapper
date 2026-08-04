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
    """The typed, checked subset of a HEXT Observation the pipeline operates on.

    RFC-MM002 SS2.1 describes ``HEXTObservation`` as a flat
    ``{observation_id, timestamp_ns, features, feature_dim, sensor_hash}``
    record. The real upstream HEXT wire format (``semantic-annotator-core``)
    is nested JSON (``object``/``evidence``/``final_seal``/``semantic``/
    ``provenance`` sections), which this type's field names
    (``text``, ``metadata``, ``content_hash``) reflect -- renaming them to
    match the RFC's flat shape would break real HEXT ingestion for no
    behavioral gain. ``feature_dim`` is added below as the one field that is
    both in the RFC and cleanly derivable. See ``docs/RFC_ALIGNMENT.md`` SS1.
    """

    observation_id: str
    text: str
    metadata: dict[str, Any]
    content_hash: str
    timestamp_ns: int
    raw_features: FloatArray = field(repr=False, compare=False)
    provenance: tuple[str, ...] = field(default_factory=tuple)

    @property
    def feature_dim(self) -> int:
        return int(self.raw_features.shape[0])
