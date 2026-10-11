"""The measurement pipeline: Validation -> ... -> MeaningMeasurement Generation.

:class:`MeaningMapperPipeline` (RFC-MM004 SS2) is the RFC-named entry point;
:func:`map_observation` is kept as a thin, backward-compatible delegate to
it (the tested public function signature predates the v2 RFC realignment).
Neither holds state across calls -- it never raises for a rejected
observation (RFC-MM001 Principle 5, Optional) -- a bad observation comes
back quarantined, and the caller's observation loop keeps running.
``previous_theta`` (RFC-MM004 SS4 Non-Discontinuity Guard) must be supplied
explicitly by the caller on every call it wants the guard evaluated for;
Meaning Mapper never remembers it. See ``docs/RFC_ALIGNMENT.md`` SS4.

The guard is time-aware only when the caller also passes ``previous_timestamp_ns``
and an explicit ``discontinuity_rate_max`` (no default exists); otherwise it is the
RFC's displacement rule, unchanged. A HEXT Observation's declared temporal context
(``semantic.metadata.time_frame``) is carried onto the MeaningMeasurement and is
never part of what is measured. See ``docs/RFC_ALIGNMENT.md`` SS8.
"""

from __future__ import annotations

from dataclasses import dataclass

from meaning_mapper._constants import DEFAULT_FRAME_ID, THETA_DISCONTINUITY_MAX
from meaning_mapper.covariance.covariance_estimation import estimate_covariance
from meaning_mapper.density.density_estimation import compute_semantic_density, estimate_density
from meaning_mapper.errors import QuarantineReason
from meaning_mapper.frame.local_frame import resolve_local_frame
from meaning_mapper.measurement.meaning_measurement import MeaningMeasurement
from meaning_mapper.metrics.metric_tensor import estimate_metric_tensor
from meaning_mapper.projection.semantic_projection import project_to_theta
from meaning_mapper.topology.topological_consistency import (
    check_discontinuity,
    check_discontinuity_over_time,
    check_topological_consistency,
)
from meaning_mapper.types import HEXTObservation
from meaning_mapper.validation.observation_validation import validate_observation
from meaning_mapper.version import __version__


@dataclass(frozen=True, slots=True)
class MeasurementResult:
    """Exactly one of ``measurement`` or ``quarantine`` is set, never both."""

    measurement: MeaningMeasurement | None
    quarantine: QuarantineReason | None

    @property
    def is_quarantined(self) -> bool:
        return self.quarantine is not None

    @property
    def is_valid(self) -> bool:
        """RFC-MM002 SS3 naming for ``not is_quarantined``."""
        return not self.is_quarantined


def _quarantined(reason: QuarantineReason) -> MeasurementResult:
    return MeasurementResult(measurement=None, quarantine=reason)


class MeaningMapperPipeline:
    """RFC-MM004 SS2: the 8-stage pipeline as a named runtime object.

    Stateless -- every call to :meth:`process` is fully independent of every
    other; the class exists to match RFC-MM004's
    ``MeaningMapperPipeline.process(observation)`` entry-point name, not to
    hold instance state (there is none to hold, per RFC-MM001's Pure
    Library & Zero Side Effects rule).
    """

    def process(
        self,
        observation: HEXTObservation,
        *,
        frame_id: str = DEFAULT_FRAME_ID,
        previous_theta: tuple[float, ...] | None = None,
        discontinuity_delta_max: float = THETA_DISCONTINUITY_MAX,
        previous_timestamp_ns: int | None = None,
        discontinuity_rate_max: float | None = None,
    ) -> MeasurementResult:
        """Run the full measurement pipeline over a single HEXT Observation.

        Passing both ``previous_timestamp_ns`` and ``discontinuity_rate_max`` (with
        ``previous_theta``) makes the Non-Discontinuity Guard judge the jump as a rate
        over the elapsed time; passing neither keeps the RFC displacement rule.
        """
        validated = validate_observation(observation)
        if isinstance(validated, QuarantineReason):
            return _quarantined(validated)

        metric_tensor = estimate_metric_tensor(
            validated.raw_features, observation_id=validated.observation_id
        )
        if isinstance(metric_tensor, QuarantineReason):  # pragma: no cover
            # raw_features comes from the deterministic hashing-trick extractor
            # in _features.py, which can only ever emit finite values, so this
            # branch is unreachable through process(). estimate_metric_tensor
            # keeps the check because it is a public function other callers can
            # invoke directly with arbitrary arrays -- see test_metric_tensor.py.
            return _quarantined(metric_tensor)

        frame = resolve_local_frame(metric_tensor, frame_id=frame_id)
        density = estimate_density(validated.raw_features)
        semantic_density = compute_semantic_density(validated.raw_features)
        covariance = estimate_covariance(frame, density)
        theta = project_to_theta(validated.raw_features, frame)

        topology_failure = check_topological_consistency(
            theta, frame, covariance, observation_id=validated.observation_id
        )
        if topology_failure is not None:
            return _quarantined(topology_failure)

        if previous_timestamp_ns is not None and discontinuity_rate_max is not None:
            discontinuity_failure = check_discontinuity_over_time(
                theta,
                previous_theta,
                timestamp_ns=validated.timestamp_ns,
                previous_timestamp_ns=previous_timestamp_ns,
                rate_max=discontinuity_rate_max,
                delta_max=discontinuity_delta_max,
                observation_id=validated.observation_id,
            )
        else:
            discontinuity_failure = check_discontinuity(
                theta,
                previous_theta,
                delta_max=discontinuity_delta_max,
                observation_id=validated.observation_id,
            )
        if discontinuity_failure is not None:
            return _quarantined(discontinuity_failure)

        # Stage 8: MeaningMeasurement Generation. theta/sigma are already finite,
        # dimension-matched, and SPD -- the Topological Consistency Check above
        # is what guarantees that, so there is nothing left here to re-validate.
        measurement = MeaningMeasurement(
            observation_id=validated.observation_id,
            frame_id=frame_id,
            theta=theta,
            sigma=covariance.matrix,
            timestamp_ns=validated.timestamp_ns,
            density=semantic_density,
            provenance=(f"meaning-mapper@{__version__}", *validated.provenance),
            temporal_context=validated.temporal_context,
        )
        return MeasurementResult(measurement=measurement, quarantine=None)


def map_observation(
    observation: HEXTObservation,
    *,
    frame_id: str = DEFAULT_FRAME_ID,
    previous_theta: tuple[float, ...] | None = None,
    discontinuity_delta_max: float = THETA_DISCONTINUITY_MAX,
    previous_timestamp_ns: int | None = None,
    discontinuity_rate_max: float | None = None,
) -> MeasurementResult:
    """Backward-compatible free-function entry point; delegates to
    :class:`MeaningMapperPipeline`."""
    return MeaningMapperPipeline().process(
        observation,
        frame_id=frame_id,
        previous_theta=previous_theta,
        discontinuity_delta_max=discontinuity_delta_max,
        previous_timestamp_ns=previous_timestamp_ns,
        discontinuity_rate_max=discontinuity_rate_max,
    )
