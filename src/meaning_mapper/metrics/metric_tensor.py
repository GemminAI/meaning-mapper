"""Stage 2: Metric Tensor Estimation.

Estimates a local metric tensor ``g`` over the raw (pre-projection) feature space:
a diagonal SPD matrix where dense feature coordinates (high raw mass, seen
often) get a *smaller* weight than sparse ones, so a unit step in a rare
coordinate counts for more than a unit step in a common one. ``g`` is what
Local Frame Resolution turns into an orthonormal basis and what Covariance
Estimation inverts into an uncertainty.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from meaning_mapper._constants import METRIC_EIGEN_CEILING, METRIC_EIGEN_FLOOR
from meaning_mapper._linalg import (
    FloatArray,
    Matrix,
    clamp_eigenvalues,
    freeze_matrix,
    matrix_array,
)
from meaning_mapper.errors import QuarantineReason, QuarantineStage


@dataclass(frozen=True, slots=True)
class MetricTensor:
    """A local, SPD metric tensor ``g`` over the raw feature space.

    ``matrix`` is a frozen ``Matrix`` tuple (RFC-MM002 Defensive Tuple
    Locking) -- ``__post_init__`` deep-copies and freezes whatever array-like
    value the constructor received, so a ``frozen=True`` dataclass field
    cannot be mutated in place the way a raw ``numpy.ndarray`` field could.
    """

    matrix: Matrix

    def __post_init__(self) -> None:
        object.__setattr__(self, "matrix", freeze_matrix(self.matrix))

    @property
    def dimension(self) -> int:
        return len(self.matrix)

    @property
    def array(self) -> FloatArray:
        """The mutable ``ndarray`` view, reconstructed on demand for math."""
        return matrix_array(self.matrix)


def estimate_metric_tensor(
    raw_features: FloatArray,
    *,
    observation_id: str | None = None,
) -> MetricTensor | QuarantineReason:
    if not np.all(np.isfinite(raw_features)):
        return QuarantineReason(
            stage=QuarantineStage.METRIC_TENSOR,
            detail="raw feature vector contains non-finite values",
            observation_id=observation_id,
        )
    diagonal = 1.0 / (1.0 + raw_features)
    raw_matrix = np.diag(diagonal)
    clamped = clamp_eigenvalues(raw_matrix, METRIC_EIGEN_FLOOR, METRIC_EIGEN_CEILING)
    return MetricTensor(matrix=freeze_matrix(clamped))
