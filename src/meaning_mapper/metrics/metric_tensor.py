"""Stage 2: Metric Tensor Estimation.

Estimates a local metric tensor ``g`` over the raw (pre-lift) feature space:
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
from meaning_mapper._linalg import FloatArray, clamp_eigenvalues
from meaning_mapper.errors import QuarantineReason, QuarantineStage


@dataclass(frozen=True, slots=True)
class MetricTensor:
    """A local, SPD metric tensor ``g`` over the raw feature space."""

    matrix: FloatArray

    @property
    def dimension(self) -> int:
        return int(self.matrix.shape[0])


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
    return MetricTensor(matrix=clamped)
