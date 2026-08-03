from __future__ import annotations

import numpy as np

from meaning_mapper._constants import DENSITY_CEILING, DENSITY_FLOOR
from meaning_mapper.density.density_estimation import estimate_density


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
