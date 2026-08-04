"""The measurement pipeline: Validation -> ... -> MeaningMeasurement Generation.

The single entry point, :func:`map_observation`, is the whole of Meaning
Mapper's public contract: HEXT Observation in, :class:`MeasurementResult`
out. It never raises for a rejected observation (RFC-MM001 Principle 5,
Optional) -- a bad observation comes back quarantined, and the caller's
observation loop keeps running.
"""

from __future__ import annotations

from dataclasses import dataclass

from meaning_mapper._constants import DEFAULT_FRAME_ID
from meaning_mapper._linalg import to_matrix_tuple
from meaning_mapper.covariance.covariance_estimation import estimate_covariance
from meaning_mapper.density.density_estimation import estimate_density
from meaning_mapper.errors import QuarantineReason
from meaning_mapper.frame.local_frame import resolve_local_frame
from meaning_mapper.measurement.meaning_measurement import MeaningMeasurement
from meaning_mapper.metrics.metric_tensor import estimate_metric_tensor
from meaning_mapper.projection.semantic_projection import project_to_theta
from meaning_mapper.topology.topological_consistency import check_topological_consistency
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


def _quarantined(reason: QuarantineReason) -> MeasurementResult:
    return MeasurementResult(measurement=None, quarantine=reason)


def map_observation(
    observation: HEXTObservation,
    *,
    frame_id: str = DEFAULT_FRAME_ID,
) -> MeasurementResult:
    """Run the full measurement pipeline over a single HEXT Observation."""
    validated = validate_observation(observation)
    if isinstance(validated, QuarantineReason):
        return _quarantined(validated)

    metric_tensor = estimate_metric_tensor(
        validated.raw_features, observation_id=validated.observation_id
    )
    if isinstance(metric_tensor, QuarantineReason):  # pragma: no cover
        # raw_features comes from the deterministic hashing-trick extractor
        # in _features.py, which can only ever emit finite values, so this
        # branch is unreachable through map_observation. estimate_metric_tensor
        # keeps the check because it is a public function other callers can
        # invoke directly with arbitrary arrays -- see test_metric_tensor.py.
        return _quarantined(metric_tensor)

    frame = resolve_local_frame(metric_tensor)
    density = estimate_density(validated.raw_features)
    covariance = estimate_covariance(metric_tensor, density)
    theta = project_to_theta(validated.raw_features, frame)

    topology_failure = check_topological_consistency(
        theta, frame, covariance, observation_id=validated.observation_id
    )
    if topology_failure is not None:
        return _quarantined(topology_failure)

    # Stage 8: MeaningMeasurement Generation. theta/sigma are already finite,
    # dimension-matched, and SPD -- the Topological Consistency Check above
    # is what guarantees that, so there is nothing left here to re-validate.
    measurement = MeaningMeasurement(
        observation_id=validated.observation_id,
        frame_id=frame_id,
        theta=theta,
        sigma=to_matrix_tuple(covariance.matrix),
        timestamp_ns=validated.timestamp_ns,
        provenance=(f"meaning-mapper@{__version__}", *validated.provenance),
    )
    return MeasurementResult(measurement=measurement, quarantine=None)
