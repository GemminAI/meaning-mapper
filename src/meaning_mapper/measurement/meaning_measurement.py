"""Stage 8: MeaningMeasurement Generation.

The output ABI. Structurally compatible with ``msr.abi.MeaningMeasurement``
(observation_id, frame_id, theta, sigma, timestamp_ns, provenance) so it
satisfies MSR's already-built, verified structural port
(``msr.adapters.mapper.measurement_from_payload``) without Meaning Mapper
importing ``msr`` -- the crossing is a shape, not a shared class.

RFC-MM002 v2 SS2.3 names this field ``covariance`` rather than ``sigma`` and
does not include ``frame_id``; both are kept as-is here because MSR's real,
already-verified wire contract uses ``sigma``/``frame_id``, and this repo
does not control that contract. ``measurement_id`` and ``provenance_hash``
are pure functions of the measurement's own defining fields (never
caller-supplied) so they cannot drift from what they describe or be spoofed.
See ``docs/RFC_ALIGNMENT.md`` SS2 for the full naming-deviation rationale,
including why ``betti_numbers`` (RFC-MM002 v2 SS2.3) is intentionally absent.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from typing import Any

from meaning_mapper._linalg import (
    Matrix,
    Vector,
    freeze_matrix,
    is_spd,
    matrix_array,
    to_vector_tuple,
)
from meaning_mapper.errors import InvariantError

_MEASUREMENT_ID_NAME_PREFIX = "urn:gemminai:meaning-mapper:measurement"


def _measurement_id(observation_id: str, frame_id: str, timestamp_ns: int) -> str:
    """Deterministic UUID5 (RFC-MM005 SS2.1 Bit-Identical Reproducibility).

    uuid4 is not usable here: it is seeded from an OS entropy source, so two
    otherwise-identical measurements would get different ids on every run.
    uuid5 is a pure hash of (namespace, name) and is bit-identical across
    processes and machines for the same inputs.
    """
    name = f"{_MEASUREMENT_ID_NAME_PREFIX}:{observation_id}:{frame_id}:{timestamp_ns}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, name))


def _provenance_hash(
    observation_id: str, frame_id: str, theta: Vector, sigma: Matrix, timestamp_ns: int
) -> str:
    """SHA-256 integrity hash over the measurement's own defining fields.

    RFC-MM002 v2 SS2.3 calls for a hash "of the input, frame, and
    computation parameters" without enumerating them; those are exactly the
    fields that determine theta/sigma, so hashing the measurement's own
    output fields is equivalent and needs no separate parameter bag.
    """
    digest = hashlib.sha256()
    digest.update(observation_id.encode("utf-8"))
    digest.update(frame_id.encode("utf-8"))
    digest.update(repr(theta).encode("utf-8"))
    digest.update(repr(sigma).encode("utf-8"))
    digest.update(str(timestamp_ns).encode("utf-8"))
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class MeaningMeasurement:
    """A single semantic measurement: Meaning Mapper's sole output type."""

    observation_id: str
    frame_id: str
    theta: Vector
    sigma: Matrix
    timestamp_ns: int
    density: float
    provenance: tuple[str, ...] = field(default_factory=tuple)
    measurement_id: str = field(default="", init=False)
    provenance_hash: str = field(default="", init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "theta", to_vector_tuple(self.theta))
        object.__setattr__(self, "sigma", freeze_matrix(self.sigma))
        object.__setattr__(
            self,
            "measurement_id",
            _measurement_id(self.observation_id, self.frame_id, self.timestamp_ns),
        )
        object.__setattr__(
            self,
            "provenance_hash",
            _provenance_hash(
                self.observation_id, self.frame_id, self.theta, self.sigma, self.timestamp_ns
            ),
        )

    @property
    def dimension(self) -> int:
        return len(self.theta)

    def validate(self) -> None:
        """Check shape and SPD-ness; raises :class:`InvariantError` on any defect."""
        if self.dimension == 0:
            raise InvariantError("theta must be non-empty")
        if not all(len(row) == self.dimension for row in self.sigma):
            raise InvariantError("sigma must be a square dimension x dimension matrix")
        if not is_spd(matrix_array(self.sigma)):
            raise InvariantError("sigma must be symmetric positive-definite")
        if not 0.0 <= self.density <= 1.0:
            raise InvariantError("density must lie in [0, 1]")

    def as_dict(self) -> dict[str, Any]:
        """The plain payload MSR's structural port (mapper adapter) accepts."""
        return {
            "measurement_id": self.measurement_id,
            "observation_id": self.observation_id,
            "frame_id": self.frame_id,
            "theta": list(self.theta),
            "sigma": [list(row) for row in self.sigma],
            "timestamp_ns": self.timestamp_ns,
            "density": self.density,
            "provenance": list(self.provenance),
            "provenance_hash": self.provenance_hash,
        }
