"""Shared HEXT Observation builder for tests."""

from __future__ import annotations

from typing import Any


def make_hext_observation(
    *,
    observation_id: str = "obs-0000000000000001",
    text: str = "the quick brown fox jumps over the lazy dog",
    metadata: dict[str, Any] | None = None,
    state_hash: str = "a" * 64,
    sealed_at: str | None = "2026-08-04T00:00:00Z",
    ledger: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    final_seal: dict[str, Any] = {"state_hash": state_hash}
    if sealed_at is not None:
        final_seal["sealed_at"] = sealed_at

    observation: dict[str, Any] = {
        "spec_version": "1.0",
        "object": {"id": observation_id, "type": "observation.hext"},
        "provenance": {
            "contributors": [{"agent": "software:semantic-annotator@1.0.0", "role": "annotator"}],
        },
        "semantic": {"metadata": metadata if metadata is not None else {}},
        "final_seal": final_seal,
        "evidence": {"format": "text/plain", "body": text},
        "ledger": ledger if ledger is not None else [{"t": 1785000000, "type": "SYSTEM"}],
    }
    return observation
