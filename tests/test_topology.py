from __future__ import annotations

import math

import numpy as np

from meaning_mapper._constants import THETA_DISCONTINUITY_MAX
from meaning_mapper.covariance.covariance_estimation import Covariance
from meaning_mapper.errors import QuarantineStage
from meaning_mapper.frame.local_frame import LocalFrame
from meaning_mapper.topology.topological_consistency import (
    check_discontinuity,
    check_topological_consistency,
)


def _consistent_triple() -> tuple[tuple[float, ...], LocalFrame, Covariance]:
    theta = (0.1, 0.2)
    frame = LocalFrame(basis=np.eye(2), metric_tensor=np.eye(2), bootstrapped=False)
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
    frame = LocalFrame(basis=np.eye(2), metric_tensor=np.eye(2), bootstrapped=False)
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
    frame = LocalFrame(basis=np.eye(2), metric_tensor=np.eye(2), bootstrapped=False)
    covariance = Covariance(matrix=np.eye(2))
    result = check_topological_consistency(theta, frame, covariance)
    assert result is not None
    assert "bounded neighborhood" in result.detail


def test_discontinuity_guard_is_noop_without_previous_theta() -> None:
    assert check_discontinuity((0.0, 0.0), None) is None


def test_discontinuity_guard_passes_within_bound() -> None:
    theta = (0.1, 0.1)
    previous = (0.0, 0.0)
    assert check_discontinuity(theta, previous, delta_max=THETA_DISCONTINUITY_MAX) is None


def test_discontinuity_guard_quarantines_large_jump() -> None:
    theta = (100.0, 100.0)
    previous = (0.0, 0.0)
    result = check_discontinuity(theta, previous, delta_max=1.0, observation_id="obs-9")
    assert result is not None
    assert result.stage is QuarantineStage.SEMANTIC_PROJECTION
    assert result.observation_id == "obs-9"
    assert "discontinuous jump" in result.detail


def test_discontinuity_guard_quarantines_dimension_mismatch() -> None:
    result = check_discontinuity((0.0, 0.0), (0.0, 0.0, 0.0))
    assert result is not None
    assert result.stage is QuarantineStage.SEMANTIC_PROJECTION
    assert "dimension" in result.detail
