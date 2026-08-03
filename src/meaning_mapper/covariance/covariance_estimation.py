"""Stage 5: Covariance Estimation.

Sigma is the metric inverse (the natural notion of "spread" dual to a
metric's notion of "distance"), scaled by ``1 / density``: sparse evidence
widens the reported uncertainty, dense evidence narrows it. The metric
tensor is guaranteed invertible and SPD by Metric Tensor Estimation's own
eigenvalue clamp, so Sigma is too -- ``validate()`` exists as the boundary
check for callers that did not go through ``estimate_covariance``, not
because this function can silently emit a broken matrix.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from meaning_mapper._constants import SIGMA_EIGEN_CEILING, SIGMA_EIGEN_FLOOR
from meaning_mapper._linalg import FloatArray, clamp_eigenvalues, is_spd
from meaning_mapper.density.density_estimation import Density
from meaning_mapper.errors import InvariantError
from meaning_mapper.metrics.metric_tensor import MetricTensor


@dataclass(frozen=True, slots=True)
class Covariance:
    """A local SPD covariance (uncertainty) matrix, Sigma."""

    matrix: FloatArray

    def validate(self) -> None:
        if not is_spd(self.matrix):
            raise InvariantError("covariance matrix is not symmetric positive-definite")


def estimate_covariance(metric_tensor: MetricTensor, density: Density) -> Covariance:
    inverse = np.linalg.inv(metric_tensor.matrix)
    scaled = inverse / density.value
    clamped = clamp_eigenvalues(scaled, SIGMA_EIGEN_FLOOR, SIGMA_EIGEN_CEILING)
    return Covariance(matrix=clamped)
