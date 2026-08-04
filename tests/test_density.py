from __future__ import annotations

import math

import numpy as np

from meaning_mapper._constants import DENSITY_CEILING, DENSITY_FLOOR
from meaning_mapper.density.density_estimation import compute_semantic_density, estimate_density


def test_estimate_density_returns_mean_when_within_band() -> None:
    result = estimate_density(np.array([1.0, 2.0, 3.0, 4.0]))
    assert result.value == 2.5
    assert not result.clamped


def test_estimate_density_floors_zero_evidence() -> None:
    result = estimate_density(np.zeros(8))
    assert result.value == DENSITY_FLOOR
    assert result.clamped


def test_estimate_density_ceils_extreme_evidence() -> None:
    result = estimate_density(np.full(8, 1.0e9))
    assert result.value == DENSITY_CEILING
    assert result.clamped


def test_compute_semantic_density_is_zero_for_all_zero_features() -> None:
    assert compute_semantic_density(np.zeros(8)) == 0.0


def test_compute_semantic_density_is_zero_for_single_element_vector() -> None:
    assert compute_semantic_density(np.array([1.0])) == 0.0


def test_compute_semantic_density_is_one_for_maximally_concentrated_evidence() -> None:
    # All mass on one coordinate: p = (1, 0, ..., 0), H(x) = 0 -> D_s = c * 1 = 1.
    raw = np.zeros(8)
    raw[0] = 1.0
    assert compute_semantic_density(raw) == 1.0


def test_compute_semantic_density_is_zero_for_uniform_evidence() -> None:
    # Uniform distribution maximizes entropy: H(x) == H_max -> D_s = c * 0 = 0.
    raw = np.ones(8)
    assert math.isclose(compute_semantic_density(raw), 0.0, abs_tol=1e-9)


def test_compute_semantic_density_is_clamped_to_unit_interval() -> None:
    raw = np.zeros(4)
    raw[0] = 1.0
    density = compute_semantic_density(raw, confidence=2.0)
    assert 0.0 <= density <= 1.0


def test_compute_semantic_density_matches_hand_computed_value() -> None:
    raw = np.array([3.0, 1.0])
    # p = (0.75, 0.25); H = -(0.75*ln0.75 + 0.25*ln0.25); H_max = ln 2.
    p = np.array([0.75, 0.25])
    expected_entropy = -float(np.sum(p * np.log(p)))
    expected = 1.0 - expected_entropy / math.log(2)
    assert math.isclose(compute_semantic_density(raw), expected, rel_tol=1e-9)
