"""Stage 4: Density Estimation.

A single scalar summarizing how much raw evidence this observation carried:
average feature mass across the raw feature vector. Covariance Estimation
scales the metric inverse by ``1 / density``, so a sparse observation (little
evidence) reports wider uncertainty than a dense one -- and the value is
always clamped so neither an empty observation nor a very dense one can send
the covariance stage's scale factor to zero or infinity.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from meaning_mapper._constants import DENSITY_CEILING, DENSITY_FLOOR
from meaning_mapper._linalg import FloatArray


@dataclass(frozen=True, slots=True)
class Density:
    """A clamped local density scalar."""

    value: float
    clamped: bool


def estimate_density(raw_features: FloatArray) -> Density:
    raw_value = float(np.mean(raw_features))
    clamped_value = min(max(raw_value, DENSITY_FLOOR), DENSITY_CEILING)
    return Density(value=clamped_value, clamped=clamped_value != raw_value)
