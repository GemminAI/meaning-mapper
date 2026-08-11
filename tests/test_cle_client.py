"""cle.client: request dispatch, response parsing, and the three typed
failure modes (unreachable, HTTP error, schema mismatch). Uses
httpx.MockTransport to inject conditions deterministically, same pattern
cognitive-port-selector's own CLE/NVS client tests use this session."""

from __future__ import annotations

import json

import httpx
import pytest

from meaning_mapper.cle.client import CLEClient
from meaning_mapper.cle.errors import CLEHTTPError, CLESchemaError, CLEUnreachableError
from meaning_mapper.cle.models import (
    ConceptInput,
    FiniteCategoryInput,
    FiveW1HOverrides,
    Morphism,
    SOKOverrides,
)
from test_cle_models import _LIFT_PAYLOAD


def _client(handler) -> CLEClient:  # type: ignore[no-untyped-def]
    return CLEClient("http://mock", transport=httpx.MockTransport(handler))


def test_health() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ok", "service": "cle", "version": "0.1.0"})

    assert _client(handler).health() == {"status": "ok", "service": "cle", "version": "0.1.0"}


def test_ground_builds_request_and_parses_response() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["json"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "semantic_state": {
                    "prompt": "p",
                    "goal": "g",
                    "five_w1h": {
                        name: {"value": "v", "source": "explicit"}
                        for name in ("who", "what", "when", "where", "why", "how")
                    },
                    "sok": {
                        "subject": "s",
                        "subject_source": "explicit",
                        "observer": "o",
                        "observer_source": "derived",
                        "knowledge_reference": "k",
                        "knowledge_reference_source": "unspecified",
                    },
                    "fingerprint": [],
                    "goal_fingerprint": [],
                    "subject_fingerprint": [],
                    "observer_fingerprint": [],
                    "knowledge_fingerprint": [],
                },
                "lift": _LIFT_PAYLOAD,
            },
        )

    result = _client(handler).ground("p", "g")
    assert seen["path"] == "/ground"
    assert seen["json"] == {
        "prompt": "p",
        "goal": "g",
        "default_knowledge_reference": "unspecified",
        "embedding_dimension": 8,
    }
    assert result.semantic_state.prompt == "p"
    assert result.lift.concept_id == "concept:abc"


def test_ground_with_overrides_included_in_payload() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["json"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "semantic_state": {
                    "prompt": "p",
                    "goal": "g",
                    "five_w1h": {
                        name: {"value": "v", "source": "explicit"}
                        for name in ("who", "what", "when", "where", "why", "how")
                    },
                    "sok": {
                        "subject": "s",
                        "subject_source": "explicit",
                        "observer": "o",
                        "observer_source": "derived",
                        "knowledge_reference": "k",
                        "knowledge_reference_source": "unspecified",
                    },
                    "fingerprint": [],
                    "goal_fingerprint": [],
                    "subject_fingerprint": [],
                    "observer_fingerprint": [],
                    "knowledge_fingerprint": [],
                },
                "lift": _LIFT_PAYLOAD,
            },
        )

    _client(handler).ground(
        "p",
        "g",
        five_w1h_overrides=FiveW1HOverrides(who="explicit-who"),
        sok_overrides=SOKOverrides(subject="explicit-subject"),
    )
    assert seen["json"]["five_w1h_overrides"] == {"who": "explicit-who"}
    assert seen["json"]["sok_overrides"] == {"subject": "explicit-subject"}


def test_lift_sends_point_cloud_payload() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["json"] = json.loads(request.content)
        return httpx.Response(200, json=_LIFT_PAYLOAD)

    result = _client(handler).lift(ConceptInput(states=((1.0, 2.0),)))
    assert seen["json"] == {"concept": {"states": [{"theta": [1.0, 2.0]}]}}
    assert result.concept_id == "concept:abc"


def test_lift_with_three_views_included_in_payload() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["json"] = json.loads(request.content)
        return httpx.Response(200, json=_LIFT_PAYLOAD)

    point = ConceptInput(states=((1.0,),))
    _client(handler).lift(
        point, subject_context=point, observer_context=point, human_knowledge_context=point
    )
    assert set(seen["json"]) == {
        "concept",
        "subject_context",
        "observer_context",
        "human_knowledge_context",
    }


def test_pullback_sends_category_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"shared_morphisms": []})

    category = FiniteCategoryInput(objects=("a",), morphisms=(Morphism("id_a", "a", "a"),))
    result = _client(handler).pullback(category, category, category)
    assert result.shared_morphisms == ()


def test_recover_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "recovered_state_id": "recovered:x",
                "reconstructed_closure": {},
                "three_view_discrepancy": 0.0,
                "converged": True,
            },
        )

    point = ConceptInput(states=((0.0,),))
    result = _client(handler).recover(point, point, point)
    assert result.converged is True


def test_recover_503_without_configured_recovery_engine_raises_http_error() -> None:
    """Matches the real CLE default app instance's documented behavior."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "recovery_engine is not configured"})

    point = ConceptInput(states=((0.0,),))
    with pytest.raises(CLEHTTPError) as exc_info:
        _client(handler).recover(point, point, point)
    assert exc_info.value.status_code == 503


def test_compress() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"raw_size": 10, "lifted_size": 2, "ratio": 5.0, "meets_target": True}
        )

    result = _client(handler).compress("raw", ["m1"])
    assert result.ratio == 5.0


def test_unreachable_raises_typed_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated CLE unreachable", request=request)

    with pytest.raises(CLEUnreachableError):
        _client(handler).ground("p", "g")


def test_http_error_raises_typed_error_with_status_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "bad request"})

    with pytest.raises(CLEHTTPError) as exc_info:
        _client(handler).ground("p", "g")
    assert exc_info.value.status_code == 422


def test_http_error_with_non_json_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal server error")

    with pytest.raises(CLEHTTPError) as exc_info:
        _client(handler).ground("p", "g")
    assert exc_info.value.body == "internal server error"


def test_malformed_response_raises_schema_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"semantic_state": {}}
        )  # missing 'lift' and required subfields

    with pytest.raises(CLESchemaError):
        _client(handler).ground("p", "g")


def test_context_manager_closes_client() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ok", "service": "cle", "version": "0.1.0"})

    with _client(handler) as client:
        client.health()
    assert client._client.is_closed
