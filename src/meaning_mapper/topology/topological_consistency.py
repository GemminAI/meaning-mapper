"""Stage 7: Topological Consistency Check.

The last gate before MeaningMeasurement Generation: confirms theta, the
local frame, and Sigma actually agree with each other before they are
packaged and handed to MSR. This is where a broken intermediate result gets
quarantined instead of silently becoming a MeaningMeasurement MSR would
have to reject on its own boundary.

``check_discontinuity`` (RFC-MM004 SS4) is a separate, stateless function:
Meaning Mapper holds no state across observations (RFC-MM001 "Pure Library &
Zero Side Effects"; ``docs/ARCHITECTURE.md``), so it never remembers a prior
theta itself. A caller that owns an observation stream (e.g. MSR, which
already assembles trajectories) MAY pass the previous measurement's theta
in explicitly; if it does not, the guard is simply not evaluated. See
``docs/RFC_ALIGNMENT.md`` for the boundary rationale.
"""

from __future__ import annotations

import math

import numpy as np

from meaning_mapper._constants import THETA_BOUND_SCALE, THETA_DISCONTINUITY_MAX
from meaning_mapper._linalg import is_spd
from meaning_mapper.covariance.covariance_estimation import Covariance
from meaning_mapper.errors import QuarantineReason, QuarantineStage
from meaning_mapper.frame.local_frame import LocalFrame


def _quarantine(
    stage: QuarantineStage, detail: str, observation_id: str | None
) -> QuarantineReason:
    return QuarantineReason(stage=stage, detail=detail, observation_id=observation_id)


def check_topological_consistency(
    theta: tuple[float, ...],
    frame: LocalFrame,
    covariance: Covariance,
    *,
    observation_id: str | None = None,
) -> QuarantineReason | None:
    if not all(math.isfinite(value) for value in theta):
        return _quarantine(
            QuarantineStage.TOPOLOGY, "theta contains non-finite values", observation_id
        )

    dimension = len(theta)
    if dimension != frame.dimension or dimension != len(covariance.matrix):
        return _quarantine(
            QuarantineStage.TOPOLOGY,
            "dimension mismatch across theta, local frame, and covariance",
            observation_id,
        )

    if not is_spd(covariance.array):
        return _quarantine(
            QuarantineStage.TOPOLOGY,
            "covariance is not symmetric positive-definite",
            observation_id,
        )

    radius = float(np.linalg.norm(theta))
    uncertainty_scale = float(np.sqrt(np.trace(covariance.array)))
    if radius > THETA_BOUND_SCALE * uncertainty_scale:
        return _quarantine(
            QuarantineStage.TOPOLOGY,
            "theta lies outside the bounded neighborhood implied by its own reported uncertainty",
            observation_id,
        )

    return None


def check_discontinuity(
    theta: tuple[float, ...],
    previous_theta: tuple[float, ...] | None,
    *,
    delta_max: float = THETA_DISCONTINUITY_MAX,
    observation_id: str | None = None,
) -> QuarantineReason | None:
    """RFC-MM004 SS4: quarantine when ``||theta_t - theta_{t-1}||_2 > delta_max``.

    Purely a function of its arguments -- Meaning Mapper never stores
    ``previous_theta`` itself. Returns ``None`` (no-op) whenever
    ``previous_theta`` is not supplied, since there is then nothing to
    compare against and no state Meaning Mapper is permitted to keep to
    obtain it.
    """
    if previous_theta is None:
        return None
    if len(previous_theta) != len(theta):
        return _quarantine(
            QuarantineStage.SEMANTIC_PROJECTION,
            "previous_theta dimension does not match theta",
            observation_id,
        )
    jump = float(np.linalg.norm(np.asarray(theta) - np.asarray(previous_theta)))
    if jump > delta_max:
        detail = (
            f"discontinuous jump ||theta_t - theta_(t-1)|| = {jump!r} > delta_max = {delta_max!r}"
        )
        return _quarantine(QuarantineStage.SEMANTIC_PROJECTION, detail, observation_id)
    return None
