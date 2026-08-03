# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

from __future__ import annotations

from fastapi.testclient import TestClient

from meaning_mapper.service import app
from meaning_mapper.version import __version__

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "meaning-mapper"
    assert body["version"] == __version__
    assert "SA001" in body["rfc"]


def test_hext_normalize_optional() -> None:
    response = client.post(
        "/hext/normalize",
        json={"document": {"hello": "world"}, "source_type": "json"},
    )
    assert response.status_code == 200
    assert "object" in response.json()
