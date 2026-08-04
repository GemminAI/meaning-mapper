"""Stage 4: Density Estimation.

Two distinct, same-stage quantities live in this module -- both named
"density" by their respective RFCs, but they are not the same number and
must not be confused (see ``docs/RFC_ALIGNMENT.md`` SS3.2):

``Density`` / ``estimate_density``
    An internal evidence-mass scalar (average raw feature mass, clamped to
    ``[DENSITY_FLOOR, DENSITY_CEILING]``), used only as Covariance
    Estimation's ``1 / density`` scale factor. Predates RFC-MM003 v2 and is
    unrelated to that RFC's ``D_s``.

``compute_semantic_density``
    RFC-MM003 SS3's ``D_s in [0, 1]``: the Shannon-entropy-based semantic
    density that becomes ``MeaningMeasurement.density``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from meaning_mapper._constants import DENSITY_CEILING, DENSITY_FLOOR
from meaning_mapper._linalg import FloatArray

# RFC-MM003 SS3 defines D_s = clamp(c * (1 - H/H_max), 0, 1) but never
# specifies where the confidence scalar `c` comes from -- the v2 pipeline
# has no external confidence/annotation input feeding Density Estimation
# (unlike the legacy RFC-SA003 payload schema, which read it from an
# annotator-supplied field). c=1.0 (full confidence) is the documented
# default for "no confidence source exists"; see docs/RFC_ALIGNMENT.md SS3.1.
SEMANTIC_DENSITY_CONFIDENCE = 1.0


@dataclass(frozen=True, slots=True)
class Density:
    """A clamped local evidence-density scalar (Covariance Estimation input)."""

    value: float
    clamped: bool


def estimate_density(raw_features: FloatArray) -> Density:
    raw_value = float(np.mean(raw_features))
    clamped_value = min(max(raw_value, DENSITY_FLOOR), DENSITY_CEILING)
    return Density(value=clamped_value, clamped=clamped_value != raw_value)


def compute_semantic_density(
    raw_features: FloatArray, *, confidence: float = SEMANTIC_DENSITY_CONFIDENCE
) -> float:
    """RFC-MM003 SS3: ``D_s = clamp(c * (1 - H(x)/H_max), 0, 1)``.

    ``H(x) = -sum p_i ln p_i``, ``p_i = |x_i| / sum_j |x_j|``, ``H_max = ln
    d``. An all-zero (or single-element) feature vector carries no evidence
    to form a distribution from -- ``p_i`` would be ``0/0`` -- so ``D_s`` is
    defined as ``0.0`` in that degenerate case, consistent with Local Frame
    Resolution's "nothing local yet" bootstrap for the same input.
    """
    dimension = raw_features.shape[0]
    magnitudes = np.abs(raw_features)
    total = float(np.sum(magnitudes))
    if dimension < 2 or total == 0.0:
        return 0.0

    probabilities = magnitudes / total
    nonzero = probabilities[probabilities > 0.0]
    entropy = -float(np.sum(nonzero * np.log(nonzero)))
    max_entropy = math.log(dimension)

    density = confidence * (1.0 - entropy / max_entropy)
    return min(max(density, 0.0), 1.0)
