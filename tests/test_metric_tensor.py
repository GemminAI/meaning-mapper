from __future__ import annotations

import numpy as np

from meaning_mapper._constants import METRIC_EIGEN_CEILING, METRIC_EIGEN_FLOOR
from meaning_mapper.errors import QuarantineReason, QuarantineStage
from meaning_mapper.metrics.metric_tensor import MetricTensor, estimate_metric_tensor


def test_estimate_metric_tensor_is_spd_and_diagonal_for_zero_features() -> None:
    result = estimate_metric_tensor(np.zeros(8))
    assert isinstance(result, MetricTensor)
    assert np.allclose(result.array, np.eye(8))


def test_estimate_metric_tensor_shrinks_dense_dimensions() -> None:
    raw = np.array([0.0, 10.0])
    result = estimate_metric_tensor(raw)
    assert isinstance(result, MetricTensor)
    assert result.matrix[1][1] < result.matrix[0][0]


def test_estimate_metric_tensor_clamps_eigenvalues() -> None:
    raw = np.array([1e12, 0.0])
    result = estimate_metric_tensor(raw)
    assert isinstance(result, MetricTensor)
    eigenvalues = np.linalg.eigvalsh(result.array)
    assert np.all(eigenvalues >= METRIC_EIGEN_FLOOR - 1e-9)
    assert np.all(eigenvalues <= METRIC_EIGEN_CEILING + 1e-6)


def test_estimate_metric_tensor_rejects_non_finite_input() -> None:
    raw = np.array([float("nan"), 1.0])
    result = estimate_metric_tensor(raw, observation_id="obs-1")
    assert isinstance(result, QuarantineReason)
    assert result.stage is QuarantineStage.METRIC_TENSOR
    assert result.observation_id == "obs-1"


def test_metric_tensor_dimension_property() -> None:
    tensor = MetricTensor(matrix=np.eye(5))
    assert tensor.dimension == 5


def test_metric_tensor_matrix_is_frozen_tuple() -> None:
    tensor = MetricTensor(matrix=np.eye(3))
    assert isinstance(tensor.matrix, tuple)
    assert all(isinstance(row, tuple) for row in tensor.matrix)


def test_metric_tensor_accepts_nested_list_input() -> None:
    tensor = MetricTensor(matrix=[[1.0, 0.0], [0.0, 1.0]])  # type: ignore[arg-type]
    assert tensor.matrix == ((1.0, 0.0), (0.0, 1.0))
