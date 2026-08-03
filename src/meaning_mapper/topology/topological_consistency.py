"""Stage 7: Topological Consistency Check.

The last gate before MeaningMeasurement Generation: confirms theta, the
local frame, and Sigma actually agree with each other before they are
packaged and handed to MSR. This is where a broken intermediate result gets
quarantined instead of silently becoming a MeaningMeasurement MSR would
have to reject on its own boundary.
"""

from __future__ import annotations

import math

import numpy as np

from meaning_mapper._constants import THETA_BOUND_SCALE
from meaning_mapper._linalg import is_spd
from meaning_mapper.covariance.covariance_estimation import Covariance
from meaning_mapper.errors import QuarantineReason, QuarantineStage
from meaning_mapper.frame.local_frame import LocalFrame


def _quarantine(detail: str, observation_id: str | None) -> QuarantineReason:
    return QuarantineReason(
        stage=QuarantineStage.TOPOLOGY, detail=detail, observation_id=observation_id
    )


def check_topological_consistency(
    theta: tuple[float, ...],
    frame: LocalFrame,
    covariance: Covariance,
    *,
    observation_id: str | None = None,
) -> QuarantineReason | None:
    if not all(math.isfinite(value) for value in theta):
        return _quarantine("theta contains non-finite values", observation_id)

    dimension = len(theta)
    if dimension != frame.dimension or dimension != covariance.matrix.shape[0]:
        return _quarantine(
            "dimension mismatch across theta, local frame, and covariance", observation_id
        )

    if not is_spd(covariance.matrix):
        return _quarantine("covariance is not symmetric positive-definite", observation_id)

    radius = float(np.linalg.norm(theta))
    uncertainty_scale = float(np.sqrt(np.trace(covariance.matrix)))
    if radius > THETA_BOUND_SCALE * uncertainty_scale:
        return _quarantine(
            "theta lies outside the bounded neighborhood implied by its own reported uncertainty",
            observation_id,
        )

    return None
