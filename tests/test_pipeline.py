from __future__ import annotations

from factories import make_hext_observation
from meaning_mapper._constants import DEFAULT_FRAME_ID
from meaning_mapper.errors import QuarantineStage
from meaning_mapper.measurement.meaning_measurement import MeaningMeasurement
from meaning_mapper.pipeline import map_observation


def test_valid_observation_produces_a_measurement() -> None:
    result = map_observation(make_hext_observation())
    assert not result.is_quarantined
    assert isinstance(result.measurement, MeaningMeasurement)
    result.measurement.validate()  # must not raise


def test_mapping_is_deterministic_across_independent_calls() -> None:
    observation = make_hext_observation()
    first = map_observation(observation)
    second = map_observation(observation)
    assert first.measurement is not None
    assert second.measurement is not None
    assert first.measurement.theta == second.measurement.theta
    assert first.measurement.sigma == second.measurement.sigma
    assert first.measurement.observation_id == second.measurement.observation_id
    assert first.measurement.timestamp_ns == second.measurement.timestamp_ns
    assert first.measurement.provenance == second.measurement.provenance


def test_default_frame_id_is_used_when_not_specified() -> None:
    result = map_observation(make_hext_observation())
    assert result.measurement is not None
    assert result.measurement.frame_id == DEFAULT_FRAME_ID


def test_custom_frame_id_is_passed_through() -> None:
    result = map_observation(make_hext_observation(), frame_id="custom.frame")
    assert result.measurement is not None
    assert result.measurement.frame_id == "custom.frame"


def test_malformed_observation_is_quarantined_not_raised() -> None:
    result = map_observation({})
    assert result.is_quarantined
    assert result.measurement is None
    assert result.quarantine is not None
    assert result.quarantine.stage is QuarantineStage.VALIDATION


def test_measurement_provenance_carries_upstream_contributors() -> None:
    result = map_observation(make_hext_observation())
    assert result.measurement is not None
    assert "software:semantic-annotator@1.0.0" in result.measurement.provenance
    assert any(entry.startswith("meaning-mapper@") for entry in result.measurement.provenance)


def test_extreme_single_token_repetition_is_quarantined_by_topology() -> None:
    # All evidentiary mass piles onto one hashed bucket, driving theta far
    # outside the neighborhood implied by its own (density-shrunk)
    # uncertainty -- a real, reachable Topological Consistency rejection,
    # not a synthetic one built by hand-constructing intermediate stages.
    observation = make_hext_observation(text=" ".join(["spike"] * 60))
    result = map_observation(observation)
    assert result.is_quarantined
    assert result.quarantine is not None
    assert result.quarantine.stage is QuarantineStage.TOPOLOGY


def test_measurement_payload_is_msr_structural_port_compatible() -> None:
    result = map_observation(make_hext_observation())
    assert result.measurement is not None
    payload = result.measurement.as_dict()
    assert isinstance(payload["theta"], list)
    assert isinstance(payload["sigma"], list)
    assert isinstance(payload["frame_id"], str)
