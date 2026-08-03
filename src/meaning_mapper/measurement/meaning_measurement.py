"""Stage 8: MeaningMeasurement Generation.

The output ABI. Field-for-field structurally identical to
``msr.abi.MeaningMeasurement`` (observation_id, frame_id, theta, sigma,
timestamp_ns, provenance) so it satisfies MSR's structural port
(``msr.adapters.mapper.measurement_from_payload``) without Meaning Mapper
importing ``msr`` -- the crossing is a shape, not a shared class.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from meaning_mapper._linalg import is_spd
from meaning_mapper.errors import InvariantError

Vector = tuple[float, ...]
Matrix = tuple[tuple[float, ...], ...]


@dataclass(frozen=True, slots=True)
class MeaningMeasurement:
    """A single semantic measurement: Meaning Mapper's sole output type."""

    observation_id: str
    frame_id: str
    theta: Vector
    sigma: Matrix
    timestamp_ns: int
    provenance: tuple[str, ...] = field(default_factory=tuple)

    @property
    def dimension(self) -> int:
        return len(self.theta)

    def validate(self) -> None:
        """Check shape and SPD-ness; raises :class:`InvariantError` on any defect."""
        if self.dimension == 0:
            raise InvariantError("theta must be non-empty")
        if not all(len(row) == self.dimension for row in self.sigma):
            raise InvariantError("sigma must be a square dimension x dimension matrix")
        if not is_spd(np.asarray(self.sigma, dtype=np.float64)):
            raise InvariantError("sigma must be symmetric positive-definite")

    def as_dict(self) -> dict[str, Any]:
        """The plain payload MSR's structural port (mapper adapter) accepts."""
        return {
            "observation_id": self.observation_id,
            "frame_id": self.frame_id,
            "theta": list(self.theta),
            "sigma": [list(row) for row in self.sigma],
            "timestamp_ns": self.timestamp_ns,
            "provenance": list(self.provenance),
        }
