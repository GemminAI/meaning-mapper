"""Observation -> GroundingContext -> CLE /ground, without inventing
anything the observation does not carry. Uses httpx.MockTransport for the
CLE leg (same pattern as test_cle_client.py); the observation side uses
real HEXT fixtures (tests/factories.py), same as the rest of this repo's
tests."""

from __future__ import annotations

import httpx
import pytest

from factories import make_hext_observation
from meaning_mapper.cle.client import CLEClient
from meaning_mapper.cle.errors import CLEHTTPError, CLESchemaError, CLEUnreachableError
from meaning_mapper.cle.grounding import (
    GroundedObservation,
    extract_grounding_context,
    ground_observation,
)
from meaning_mapper.cle.models import FiveW1HOverrides, SOKOverrides
from meaning_mapper.errors import QuarantineReason, QuarantineStage
from test_cle_models import _FIVE_W1H_PAYLOAD, _LIFT_PAYLOAD, _SOK_PAYLOAD


def _client(handler) -> CLEClient:  # type: ignore[no-untyped-def]
    return CLEClient("http://mock", transport=httpx.MockTransport(handler))


def _ground_response_json(prompt: str, goal: str) -> dict:  # type: ignore[type-arg]
    return {
        "semantic_state": {
            "prompt": prompt,
            "goal": goal,
            "five_w1h": _FIVE_W1H_PAYLOAD,
            "sok": _SOK_PAYLOAD,
            "fingerprint": [],
            "goal_fingerprint": [],
            "subject_fingerprint": [],
            "observer_fingerprint": [],
            "knowledge_fingerprint": [],
        },
        "lift": _LIFT_PAYLOAD,
    }


# --- extract_grounding_context: real-observation -> real-fields-only -------


def test_extract_grounding_context_carries_observed_fields_unmodified() -> None:
    observation = make_hext_observation(
        observation_id="obs-real-0001",
        text="the quick brown fox jumps over the lazy dog",
        metadata={"lang": "en"},
        state_hash="b" * 64,
    )
    context = extract_grounding_context(observation, goal="answer a question")

    assert not isinstance(context, QuarantineReason)
    assert context.observation_id == "obs-real-0001"
    assert context.text == "the quick brown fox jumps over the lazy dog"
    assert context.goal == "answer a question"  # caller-supplied, not derived from text
    assert context.metadata == {"lang": "en"}
    assert context.state_hash == "b" * 64
    assert context.provenance == ("software:semantic-annotator@1.0.0",)


def test_extract_grounding_context_absent_metadata_stays_empty_not_fabricated() -> None:
    observation = make_hext_observation(metadata=None)
    context = extract_grounding_context(observation, goal="g")
    assert not isinstance(context, QuarantineReason)
    assert context.metadata == {}


def test_extract_grounding_context_absent_overrides_stay_none() -> None:
    """Nothing in a HEXT Observation carries S/O/K(t) or 5W1H -- absent
    stays None, not guessed from metadata content."""
    observation = make_hext_observation(metadata={"unrelated_key": "unrelated_value"})
    context = extract_grounding_context(observation, goal="g")
    assert not isinstance(context, QuarantineReason)
    assert context.five_w1h_overrides is None
    assert context.sok_overrides is None


def test_extract_grounding_context_explicit_overrides_pass_through_unmodified() -> None:
    observation = make_hext_observation()
    five_w1h = FiveW1HOverrides(who="explicit-who")
    sok = SOKOverrides(subject="explicit-subject")
    context = extract_grounding_context(
        observation, goal="g", five_w1h_overrides=five_w1h, sok_overrides=sok
    )
    assert not isinstance(context, QuarantineReason)
    assert context.five_w1h_overrides is five_w1h
    assert context.sok_overrides is sok


def test_extract_grounding_context_malformed_observation_quarantines() -> None:
    """Reuses validate_observation's own quarantine semantics -- no new
    failure mode invented for grounding specifically."""
    result = extract_grounding_context({"object": {}}, goal="g")
    assert isinstance(result, QuarantineReason)
    assert result.stage == QuarantineStage.VALIDATION


# --- ground_observation: full path, mocked CLE transport -------------------


def test_ground_observation_success() -> None:
    observation = make_hext_observation(text="observed text", observation_id="obs-0042")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_ground_response_json("observed text", "the goal"))

    result = ground_observation(_client(handler), observation, goal="the goal")

    assert isinstance(result, GroundedObservation)
    assert result.observation_id == "obs-0042"
    assert result.provenance == ("software:semantic-annotator@1.0.0",)
    assert result.grounded.semantic_state.prompt == "observed text"
    assert result.grounded.lift.concept_id == "concept:abc"


def test_ground_observation_preserves_identity_distinct_from_cle_identity() -> None:
    """Principle 6/5: the source Observation's identity is preserved
    alongside, not replaced by, CLE's own concept_id -- and this is not a
    MeaningMeasurement (no theta/sigma anywhere on GroundedObservation)."""
    observation = make_hext_observation(observation_id="obs-distinct", state_hash="c" * 64)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json=_ground_response_json("the quick brown fox jumps over the lazy dog", "g")
        )

    result = ground_observation(_client(handler), observation, goal="g")

    assert isinstance(result, GroundedObservation)
    assert result.observation_id == "obs-distinct"  # source identity
    assert result.state_hash == "c" * 64  # source content hash
    assert result.grounded.lift.concept_id == "concept:abc"  # CLE's own identity, kept separate
    assert not hasattr(result, "theta")
    assert not hasattr(result, "sigma")


def test_ground_observation_quarantines_malformed_observation_without_calling_cle() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json=_ground_response_json("x", "g"))

    result = ground_observation(_client(handler), {"object": {}}, goal="g")

    assert isinstance(result, QuarantineReason)
    assert calls == []  # CLE was never called for an unusable observation


def test_ground_observation_unreachable_propagates_typed_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated CLE unreachable", request=request)

    with pytest.raises(CLEUnreachableError):
        ground_observation(_client(handler), make_hext_observation(), goal="g")


def test_ground_observation_http_error_propagates_typed_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "bad request"})

    with pytest.raises(CLEHTTPError) as exc_info:
        ground_observation(_client(handler), make_hext_observation(), goal="g")
    assert exc_info.value.status_code == 422


def test_ground_observation_timeout_propagates_typed_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("simulated timeout", request=request)

    with pytest.raises(CLEUnreachableError):
        ground_observation(_client(handler), make_hext_observation(), goal="g")


def test_ground_observation_malformed_response_propagates_schema_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"semantic_state": {}}
        )  # missing 'lift' and required subfields

    with pytest.raises(CLESchemaError):
        ground_observation(_client(handler), make_hext_observation(), goal="g")


def test_ground_observation_5xx_propagates_typed_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal server error")

    with pytest.raises(CLEHTTPError) as exc_info:
        ground_observation(_client(handler), make_hext_observation(), goal="g")
    assert exc_info.value.status_code == 500
