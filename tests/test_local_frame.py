from __future__ import annotations

import numpy as np

from meaning_mapper.frame.local_frame import LocalFrame, resolve_local_frame
from meaning_mapper.metrics.metric_tensor import MetricTensor


def test_resolve_local_frame_whitens_metric() -> None:
    metric = MetricTensor(matrix=np.diag([4.0, 9.0]))
    frame = resolve_local_frame(metric)
    assert not frame.bootstrapped
    assert np.allclose(frame.basis @ metric.matrix @ frame.basis.T, np.eye(2), atol=1e-8)


def test_resolve_local_frame_identity_for_zero_evidence() -> None:
    metric = MetricTensor(matrix=np.eye(8))
    frame = resolve_local_frame(metric)
    assert np.allclose(frame.basis, np.eye(8))
    assert not frame.bootstrapped


def test_resolve_local_frame_bootstraps_on_non_spd_matrix() -> None:
    # A matrix Cholesky rejects (negative eigenvalue), bypassing the normal
    # clamped path -- exercises the defensive bootstrap fallback directly.
    pathological = MetricTensor(matrix=np.array([[1.0, 2.0], [2.0, 1.0]]))
    frame = resolve_local_frame(pathological)
    assert frame.bootstrapped
    assert np.allclose(frame.basis, np.eye(2))


def test_local_frame_dimension_property() -> None:
    frame = LocalFrame(basis=np.eye(3), bootstrapped=False)
    assert frame.dimension == 3
