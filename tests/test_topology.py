from __future__ import annotations

import math

import numpy as np

from meaning_mapper.covariance.covariance_estimation import Covariance
from meaning_mapper.errors import QuarantineStage
from meaning_mapper.frame.local_frame import LocalFrame
from meaning_mapper.topology.topological_consistency import check_topological_consistency


def _consistent_triple() -> tuple[tuple[float, ...], LocalFrame, Covariance]:
    theta = (0.1, 0.2)
    frame = LocalFrame(basis=np.eye(2), bootstrapped=False)
    covariance = Covariance(matrix=np.eye(2))
    return theta, frame, covariance


def test_consistent_inputs_pass() -> None:
    theta, frame, covariance = _consistent_triple()
    assert check_topological_consistency(theta, frame, covariance) is None


def test_non_finite_theta_is_quarantined() -> None:
    _, frame, covariance = _consistent_triple()
    theta = (math.nan, 0.2)
    result = check_topological_consistency(theta, frame, covariance, observation_id="obs-1")
    assert result is not None
    assert result.stage is QuarantineStage.TOPOLOGY
    assert result.observation_id == "obs-1"


def test_dimension_mismatch_is_quarantined() -> None:
    theta = (0.1, 0.2, 0.3)
    frame = LocalFrame(basis=np.eye(2), bootstrapped=False)
    covariance = Covariance(matrix=np.eye(2))
    result = check_topological_consistency(theta, frame, covariance)
    assert result is not None
    assert "dimension" in result.detail


def test_non_spd_covariance_is_quarantined() -> None:
    theta, frame, _ = _consistent_triple()
    broken_covariance = Covariance(matrix=np.array([[1.0, 2.0], [2.0, 1.0]]))
    result = check_topological_consistency(theta, frame, broken_covariance)
    assert result is not None
    assert "positive-definite" in result.detail


def test_theta_outside_uncertainty_bound_is_quarantined() -> None:
    theta = (1000.0, 1000.0)
    frame = LocalFrame(basis=np.eye(2), bootstrapped=False)
    covariance = Covariance(matrix=np.eye(2))
    result = check_topological_consistency(theta, frame, covariance)
    assert result is not None
    assert "bounded neighborhood" in result.detail
