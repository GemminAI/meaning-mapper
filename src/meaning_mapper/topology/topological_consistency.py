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

``check_discontinuity_over_time`` is the opt-in, time-aware form of the same
guard: a jump of a given size is judged against the time that actually elapsed
between the two measurements (a rate), so a large but legitimate move across a
large gap is not mistaken for an artifact. It is equally stateless -- the caller
passes the previous timestamp in alongside the previous theta -- and it has no
default threshold: no numeric rate bound is specified anywhere, so none is invented.
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


def check_discontinuity_over_time(
    theta: tuple[float, ...],
    previous_theta: tuple[float, ...] | None,
    *,
    timestamp_ns: int,
    previous_timestamp_ns: int,
    rate_max: float,
    delta_max: float = THETA_DISCONTINUITY_MAX,
    observation_id: str | None = None,
) -> QuarantineReason | None:
    """Time-aware Non-Discontinuity Guard: quarantine when
    ``||theta_t - theta_(t-1)||_2 / dt > rate_max`` (theta units per second).

    ``dt`` is ``(timestamp_ns - previous_timestamp_ns)`` in seconds. Purely a
    function of its arguments, like :func:`check_discontinuity`.

    - no ``previous_theta``: no-op (``None``).
    - ``dt < 0``: quarantined -- the previous measurement is later than this one,
      so no rate exists and the pair is not in observation order.
    - ``dt == 0``: no rate exists (two observations sealed within the same clock
      tick), so this falls back to the displacement rule of
      :func:`check_discontinuity` with ``delta_max`` rather than inventing a speed.
    """
    if previous_theta is None:
        return None
    if len(previous_theta) != len(theta):
        return _quarantine(
            QuarantineStage.SEMANTIC_PROJECTION,
            "previous_theta dimension does not match theta",
            observation_id,
        )
    elapsed_ns = timestamp_ns - previous_timestamp_ns
    if elapsed_ns < 0:
        detail = (
            f"previous_timestamp_ns {previous_timestamp_ns!r} is later than "
            f"timestamp_ns {timestamp_ns!r}: observations are not in time order"
        )
        return _quarantine(QuarantineStage.SEMANTIC_PROJECTION, detail, observation_id)
    if elapsed_ns == 0:
        return check_discontinuity(
            theta, previous_theta, delta_max=delta_max, observation_id=observation_id
        )
    jump = float(np.linalg.norm(np.asarray(theta) - np.asarray(previous_theta)))
    rate = jump / (elapsed_ns / 1e9)
    if rate > rate_max:
        detail = (
            f"discontinuous rate ||theta_t - theta_(t-1)|| / dt = {rate!r} per second "
            f"> rate_max = {rate_max!r} (jump {jump!r} over {elapsed_ns / 1e9!r} s)"
        )
        return _quarantine(QuarantineStage.SEMANTIC_PROJECTION, detail, observation_id)
    return None
