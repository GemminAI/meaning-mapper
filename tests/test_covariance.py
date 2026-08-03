from __future__ import annotations

import numpy as np
import pytest

from meaning_mapper._constants import SIGMA_EIGEN_CEILING, SIGMA_EIGEN_FLOOR
from meaning_mapper.covariance.covariance_estimation import Covariance, estimate_covariance
from meaning_mapper.density.density_estimation import Density
from meaning_mapper.errors import InvariantError
from meaning_mapper.metrics.metric_tensor import MetricTensor


def test_estimate_covariance_is_spd() -> None:
    metric = MetricTensor(matrix=np.diag([2.0, 4.0]))
    density = Density(value=1.0, clamped=False)
    covariance = estimate_covariance(metric, density)
    covariance.validate()  # must not raise


def test_estimate_covariance_scales_inversely_with_density() -> None:
    metric = MetricTensor(matrix=np.eye(4))
    sparse = estimate_covariance(metric, Density(value=0.5, clamped=False))
    dense = estimate_covariance(metric, Density(value=5.0, clamped=False))
    assert sparse.matrix[0, 0] > dense.matrix[0, 0]


def test_estimate_covariance_clamps_eigenvalues() -> None:
    metric = MetricTensor(matrix=np.diag([1e-3, 1e3]))
    covariance = estimate_covariance(metric, Density(value=1e-3, clamped=True))
    eigenvalues = np.linalg.eigvalsh(covariance.matrix)
    assert np.all(eigenvalues >= SIGMA_EIGEN_FLOOR - 1e-9)
    assert np.all(eigenvalues <= SIGMA_EIGEN_CEILING + 1e-3)


def test_covariance_validate_raises_for_non_spd_matrix() -> None:
    broken = Covariance(matrix=np.array([[1.0, 2.0], [2.0, 1.0]]))
    with pytest.raises(InvariantError):
        broken.validate()
