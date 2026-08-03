"""Stage 1: Observation Validation.

Owns receiving a HEXT Observation and checking it carries what every later
stage needs: a stable id, measurable content, a content hash, and a
timestamp. Nothing here interprets meaning -- that starts at Metric Tensor
Estimation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from meaning_mapper._features import raw_features
from meaning_mapper.errors import QuarantineReason, QuarantineStage
from meaning_mapper.types import HEXTObservation, ValidatedObservation


def _quarantine(detail: str, observation_id: str | None = None) -> QuarantineReason:
    return QuarantineReason(
        stage=QuarantineStage.VALIDATION, detail=detail, observation_id=observation_id
    )


def _section(observation: HEXTObservation, key: str) -> Any:
    value = observation.get(key)
    return value if isinstance(value, dict) else None


def _timestamp_ns(final_seal: dict[str, Any] | None, ledger: Any) -> int | None:
    if final_seal is not None:
        sealed_at = final_seal.get("sealed_at")
        if isinstance(sealed_at, str):
            try:
                normalized = sealed_at.replace("Z", "+00:00")
                return int(datetime.fromisoformat(normalized).timestamp() * 1_000_000_000)
            except ValueError:
                pass
    if isinstance(ledger, list) and ledger:
        first_entry = ledger[0]
        if isinstance(first_entry, dict):
            seconds = first_entry.get("t")
            if isinstance(seconds, int):
                return seconds * 1_000_000_000
    return None


def _provenance(provenance_section: dict[str, Any] | None) -> tuple[str, ...]:
    if provenance_section is None:
        return ()
    contributors = provenance_section.get("contributors")
    if not isinstance(contributors, list):
        return ()
    agents = [
        contributor["agent"]
        for contributor in contributors
        if isinstance(contributor, dict) and isinstance(contributor.get("agent"), str)
    ]
    return tuple(agents)


def validate_observation(
    observation: HEXTObservation,
) -> ValidatedObservation | QuarantineReason:
    """Validate ``observation`` and extract the fields every stage depends on."""
    if not isinstance(observation, dict):
        return _quarantine("HEXT Observation must be a mapping")

    object_section = _section(observation, "object")
    if object_section is None:
        return _quarantine("missing 'object' section")
    observation_id = object_section.get("id")
    if not isinstance(observation_id, str) or not observation_id:
        return _quarantine("missing or empty 'object.id'")

    evidence_section = _section(observation, "evidence")
    if evidence_section is None:
        return _quarantine("missing 'evidence' section", observation_id)
    text = evidence_section.get("body")
    if not isinstance(text, str):
        return _quarantine("'evidence.body' must be a string", observation_id)

    final_seal_section = _section(observation, "final_seal")
    if final_seal_section is None:
        return _quarantine("missing 'final_seal' section", observation_id)
    content_hash = final_seal_section.get("state_hash")
    if not isinstance(content_hash, str) or not content_hash:
        return _quarantine("missing or empty 'final_seal.state_hash'", observation_id)

    timestamp_ns = _timestamp_ns(final_seal_section, observation.get("ledger"))
    if timestamp_ns is None:
        return _quarantine(
            "no usable timestamp in 'final_seal.sealed_at' or 'ledger[0].t'", observation_id
        )

    semantic_section = _section(observation, "semantic")
    metadata_raw = semantic_section.get("metadata") if semantic_section is not None else None
    metadata: dict[str, Any] = metadata_raw if isinstance(metadata_raw, dict) else {}

    provenance = _provenance(_section(observation, "provenance"))

    return ValidatedObservation(
        observation_id=observation_id,
        text=text,
        metadata=metadata,
        content_hash=content_hash,
        timestamp_ns=timestamp_ns,
        raw_features=raw_features(text, metadata),
        provenance=provenance,
    )
