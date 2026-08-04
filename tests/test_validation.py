from __future__ import annotations

from factories import make_hext_observation
from meaning_mapper.errors import QuarantineReason, QuarantineStage
from meaning_mapper.types import ValidatedObservation
from meaning_mapper.validation.observation_validation import _timestamp_ns, validate_observation


def test_valid_observation_is_extracted() -> None:
    result = validate_observation(make_hext_observation(observation_id="obs-123"))
    assert isinstance(result, ValidatedObservation)
    assert result.observation_id == "obs-123"
    assert result.text == "the quick brown fox jumps over the lazy dog"
    assert result.content_hash == "a" * 64
    assert result.provenance == ("software:semantic-annotator@1.0.0",)
    assert result.raw_features.shape == (8,)
    assert result.feature_dim == 8


def test_non_mapping_observation_is_quarantined() -> None:
    result = validate_observation("not a mapping")  # type: ignore[arg-type]
    assert isinstance(result, QuarantineReason)
    assert result.stage is QuarantineStage.VALIDATION


def test_missing_object_section_is_quarantined() -> None:
    observation = make_hext_observation()
    del observation["object"]
    result = validate_observation(observation)
    assert isinstance(result, QuarantineReason)
    assert "object" in result.detail


def test_missing_object_id_is_quarantined() -> None:
    observation = make_hext_observation()
    observation["object"] = {"type": "observation.hext"}
    result = validate_observation(observation)
    assert isinstance(result, QuarantineReason)


def test_empty_object_id_is_quarantined() -> None:
    observation = make_hext_observation()
    observation["object"]["id"] = ""
    result = validate_observation(observation)
    assert isinstance(result, QuarantineReason)


def test_missing_evidence_section_is_quarantined() -> None:
    observation = make_hext_observation()
    del observation["evidence"]
    result = validate_observation(observation)
    assert isinstance(result, QuarantineReason)
    assert result.observation_id == "obs-0000000000000001"


def test_non_string_evidence_body_is_quarantined() -> None:
    observation = make_hext_observation()
    observation["evidence"]["body"] = {"not": "a string"}
    result = validate_observation(observation)
    assert isinstance(result, QuarantineReason)


def test_missing_final_seal_is_quarantined() -> None:
    observation = make_hext_observation()
    del observation["final_seal"]
    result = validate_observation(observation)
    assert isinstance(result, QuarantineReason)


def test_missing_state_hash_is_quarantined() -> None:
    observation = make_hext_observation()
    del observation["final_seal"]["state_hash"]
    result = validate_observation(observation)
    assert isinstance(result, QuarantineReason)


def test_missing_timestamp_sources_is_quarantined() -> None:
    observation = make_hext_observation(sealed_at=None, ledger=[])
    result = validate_observation(observation)
    assert isinstance(result, QuarantineReason)
    assert "timestamp" in result.detail


def test_timestamp_falls_back_to_ledger() -> None:
    observation = make_hext_observation(sealed_at=None, ledger=[{"t": 1785000000}])
    result = validate_observation(observation)
    assert isinstance(result, ValidatedObservation)
    assert result.timestamp_ns == 1785000000 * 1_000_000_000


def test_malformed_sealed_at_falls_back_to_ledger() -> None:
    observation = make_hext_observation(sealed_at="not-a-timestamp", ledger=[{"t": 42}])
    result = validate_observation(observation)
    assert isinstance(result, ValidatedObservation)
    assert result.timestamp_ns == 42 * 1_000_000_000


def test_missing_semantic_metadata_defaults_to_empty_dict() -> None:
    observation = make_hext_observation()
    del observation["semantic"]
    result = validate_observation(observation)
    assert isinstance(result, ValidatedObservation)
    assert result.metadata == {}


def test_missing_provenance_defaults_to_empty_tuple() -> None:
    observation = make_hext_observation()
    del observation["provenance"]
    result = validate_observation(observation)
    assert isinstance(result, ValidatedObservation)
    assert result.provenance == ()


def test_timestamp_ns_falls_back_when_final_seal_is_absent() -> None:
    assert _timestamp_ns(None, [{"t": 5}]) == 5 * 1_000_000_000


def test_timestamp_ns_none_when_ledger_entry_is_not_a_mapping() -> None:
    assert _timestamp_ns(None, ["not-a-dict"]) is None


def test_timestamp_ns_none_when_ledger_t_is_not_an_int() -> None:
    assert _timestamp_ns(None, [{"t": "not-an-int"}]) is None


def test_provenance_ignores_malformed_contributors() -> None:
    observation = make_hext_observation()
    observation["provenance"]["contributors"] = "not-a-list"
    result = validate_observation(observation)
    assert isinstance(result, ValidatedObservation)
    assert result.provenance == ()
