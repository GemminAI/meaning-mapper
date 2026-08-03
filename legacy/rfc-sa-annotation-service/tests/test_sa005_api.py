# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""RFC-SA005 server + HTTPRuntimeBridge verification matrix."""

from __future__ import annotations

import json

import httpx
from fastapi.testclient import TestClient

from meaning_mapper.runtime_bridge import HTTPRuntimeBridge
from meaning_mapper.service import app

client = TestClient(app)

SAMPLE_REQ = {
    "client_id": "gemminai-exp5000-node-01",
    "observation_id": "obs_9482_f102",
    "prompt_id": "prompt_stability_analysis_v1",
    "timestamp": "2026-07-17T20:23:00Z",
    "raw_observational_data": {
        "acceleration": [0.01, -0.05, 9.81],
        "voltage": 12.45,
        "state_hash": "0xDEADBEEF",
    },
}


def test_api_v1_annotate_shape() -> None:
    response = client.post("/api/v1/annotate", json=SAMPLE_REQ)
    assert response.status_code == 200
    body = response.json()
    assert body["schema_id"].startswith("urn:gemminai:schema:sa003:")
    assert body["version"] == "1.0"
    assert body["annotation_id"]
    assert "coordinates" in body
    assert 0.0 <= body["semantic_density"] <= 1.0
    assert "payload_snapshot" in body
    assert body["payload_snapshot"]["generator_signature"]


def test_map_canonical_same_contract() -> None:
    a = client.post("/api/v1/annotate", json=SAMPLE_REQ).json()
    b = client.post("/map", json=SAMPLE_REQ).json()
    assert a["annotation_id"] == b["annotation_id"]
    assert a["semantic_density"] == b["semantic_density"]


def test_annotate_deprecated() -> None:
    response = client.post("/annotate", json=SAMPLE_REQ)
    assert response.status_code == 200
    assert response.json()["annotation_id"]


def test_reproducible() -> None:
    a = client.post("/map", json=SAMPLE_REQ).json()
    b = client.post("/map", json=SAMPLE_REQ).json()
    assert a == b


def test_sa005_timeout_fallback() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout", request=request)

    transport = httpx.MockTransport(handler)
    sleeps: list[float] = []
    bridge = HTTPRuntimeBridge(
        "http://annotator.test/api/v1/annotate",
        api_key="k",
        timeout_seconds=0.01,
        max_attempts=3,
        t0=0.01,
        t_max=0.05,
        sleep_fn=sleeps.append,
        transport=transport,
    )
    view = bridge.fetch_and_bridge("obs", "prompt", {"x": 1})
    assert view.annotation_id == ""
    assert view.payload_snapshot == {}
    assert bridge.last_attempts == 3


def test_sa005_exponential_retry() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, json={"error": "down"})

    sleeps: list[float] = []
    bridge = HTTPRuntimeBridge(
        "http://annotator.test/api/v1/annotate",
        max_attempts=5,
        t0=1.0,
        t_max=16.0,
        sleep_fn=sleeps.append,
        transport=httpx.MockTransport(handler),
    )
    view = bridge.fetch_and_bridge("obs", "prompt", {"x": 1})
    assert view.annotation_id == ""
    assert calls["n"] == 5
    assert len(sleeps) == 5
    # Backoff grows (allowing jitter): later waits generally >= earlier bases
    assert sleeps[-1] >= sleeps[0]


def test_sa005_rate_limiting_adherence() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "2"}, json={})
        return httpx.Response(
            200,
            json={
                "version": "1.0",
                "annotation_id": "after_wait",
                "source_type": "mock",
                "coordinates": [],
                "semantic_density": 0.5,
                "payload_snapshot": {
                    "schema_id": "urn:gemminai:schema:sa003:1.0",
                    "payload_class": "evaluative",
                    "generator_signature": "mock",
                    "confidence": 0.5,
                },
            },
        )

    sleeps: list[float] = []
    bridge = HTTPRuntimeBridge(
        "http://annotator.test/api/v1/annotate",
        sleep_fn=sleeps.append,
        transport=httpx.MockTransport(handler),
    )
    view = bridge.fetch_and_bridge("obs", "prompt", {"x": 1})
    assert view.annotation_id == "after_wait"
    assert sleeps[0] == 2.0


def test_http_bridge_success() -> None:
    """Client bridge happy path against a MockTransport SA005 responder."""
    from meaning_mapper.engine.deterministic import DeterministicAnnotatorEngine
    from meaning_mapper.runtime_bridge import StandardRuntimeBridge

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        wire = DeterministicAnnotatorEngine().annotate(
            observation_id=body["observation_id"],
            prompt_id=body["prompt_id"],
            raw_observational_data=body["raw_observational_data"],
            client_id=body.get("client_id", ""),
            timestamp=body.get("timestamp"),
        )
        return httpx.Response(200, json=StandardRuntimeBridge().bridge_annotation(wire).to_wire())

    bridge = HTTPRuntimeBridge(
        "http://annotator.test/api/v1/annotate",
        sleep_fn=lambda _s: None,
        transport=httpx.MockTransport(handler),
    )
    view = bridge.fetch_and_bridge(
        SAMPLE_REQ["observation_id"],
        SAMPLE_REQ["prompt_id"],
        SAMPLE_REQ["raw_observational_data"],
        timestamp=SAMPLE_REQ["timestamp"],
    )
    assert view.annotation_id
    assert view.coordinates == (0.01, -0.05, 9.81)
