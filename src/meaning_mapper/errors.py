"""Quarantine reasons: how Meaning Mapper reports "no measurement" without raising.

Per RFC-MM001 Principle 5 (Optional), a HEXT Observation that cannot be
measured MUST yield a neutral empty result, not an exception that stops the
observation loop. Every pipeline stage that can fail returns a
:class:`QuarantineReason` instead of raising.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class QuarantineStage(StrEnum):
    """Which stage of the measurement pipeline quarantined the observation."""

    VALIDATION = "validation"
    METRIC_TENSOR = "metric_tensor"
    LOCAL_FRAME = "local_frame"
    DENSITY = "density"
    COVARIANCE = "covariance"
    CATEGORICAL_LIFT = "categorical_lift"
    TOPOLOGY = "topology"
    MEASUREMENT = "measurement"


@dataclass(frozen=True, slots=True)
class QuarantineReason:
    """Why a HEXT Observation did not produce a MeaningMeasurement."""

    stage: QuarantineStage
    detail: str
    observation_id: str | None = None


class InvariantError(ValueError):
    """A value that should be internally guaranteed turned out not to hold.

    Distinct from :class:`QuarantineReason`: that channel is for expected,
    data-driven rejections of a HEXT Observation. This is for a stage's own
    output failing the invariant it promises callers (e.g. an SPD matrix
    that is not, in fact, SPD) -- a programmer-error-class defect, not a bad
    observation.
    """
