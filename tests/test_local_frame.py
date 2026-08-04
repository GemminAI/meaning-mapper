from __future__ import annotations

import numpy as np

from meaning_mapper.frame.local_frame import LocalFrame, resolve_local_frame
from meaning_mapper.metrics.metric_tensor import MetricTensor


def test_resolve_local_frame_whitens_metric() -> None:
    metric = MetricTensor(matrix=np.diag([4.0, 9.0]))
    frame = resolve_local_frame(metric)
    assert not frame.bootstrapped
    assert np.allclose(frame.array @ metric.array @ frame.array.T, np.eye(2), atol=1e-8)


def test_resolve_local_frame_identity_for_zero_evidence() -> None:
    metric = MetricTensor(matrix=np.eye(8))
    frame = resolve_local_frame(metric)
    assert np.allclose(frame.array, np.eye(8))
    assert not frame.bootstrapped


def test_resolve_local_frame_bootstraps_on_non_spd_matrix() -> None:
    # A matrix Cholesky rejects (negative eigenvalue), bypassing the normal
    # clamped path -- exercises the defensive bootstrap fallback directly.
    pathological = MetricTensor(matrix=np.array([[1.0, 2.0], [2.0, 1.0]]))
    frame = resolve_local_frame(pathological)
    assert frame.bootstrapped
    assert np.allclose(frame.array, np.eye(2))


def test_resolve_local_frame_default_frame_id() -> None:
    metric = MetricTensor(matrix=np.eye(2))
    frame = resolve_local_frame(metric)
    assert frame.frame_id == "meaning-mapper.default"


def test_resolve_local_frame_custom_frame_id() -> None:
    metric = MetricTensor(matrix=np.eye(2))
    frame = resolve_local_frame(metric, frame_id="custom-frame")
    assert frame.frame_id == "custom-frame"


def test_local_frame_dimension_property() -> None:
    frame = LocalFrame(basis=np.eye(3), metric_tensor=np.eye(3), bootstrapped=False)
    assert frame.dimension == 3


def test_local_frame_ambient_and_semantic_dim_match_matrices() -> None:
    frame = LocalFrame(basis=np.eye(3), metric_tensor=np.eye(3), bootstrapped=False)
    assert frame.ambient_dim == 3
    assert frame.semantic_dim == 3


def test_local_frame_basis_and_metric_tensor_are_frozen_tuples() -> None:
    frame = LocalFrame(basis=np.eye(2), metric_tensor=np.eye(2), bootstrapped=False)
    assert isinstance(frame.basis, tuple)
    assert isinstance(frame.metric_tensor, tuple)
    assert all(isinstance(row, tuple) for row in frame.basis)
