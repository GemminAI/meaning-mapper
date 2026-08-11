"""Bridges a HEXT Observation to CLE's `POST /ground`, without inferring
anything the observation does not actually carry.

Reuses `meaning_mapper.validation.observation_validation.validate_observation`
(the existing, already-tested Stage 1) rather than re-parsing HEXT -- a
malformed observation quarantines exactly the same way it would for
measurement (`QuarantineReason`, `stage=VALIDATION`), not a new failure
mode invented here.

`goal` is not a HEXT Observation field. The real wire format
(`object`/`evidence`/`final_seal`/`semantic`/`provenance`) has no goal
section (confirmed absent, Phase 1 audit) -- it is never derived from
`text`, and this module does not invent one. Callers supply it explicitly,
the same way `cognitive-port-selector`'s own `CycleRequest` always has
`goal` as a field independent of `prompt`. CLE's `GroundRequest` requires
`goal` as a non-optional string; a caller with no goal to supply must pass
one explicitly (e.g. `""`) and is not defaulted to that here.

S/O/K(t) and 5W1H are optional CALLER-supplied overrides, mirroring CLE's
own `GroundRequest` shape exactly. Neither is auto-extracted from
`metadata` -- no confirmed schema maps any `metadata` key to either
concept (Phase 1 audit: NOT FOUND), so attempting that mapping here would
be exactly the "guess and fill in" this phase forbids.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from meaning_mapper.cle.client import CLEClient
from meaning_mapper.cle.models import FiveW1HOverrides, GroundResult, SOKOverrides
from meaning_mapper.errors import QuarantineReason
from meaning_mapper.types import HEXTObservation
from meaning_mapper.validation.observation_validation import validate_observation


@dataclass(frozen=True, slots=True)
class GroundingContext:
    """Exactly what was actually observed (plus the caller-supplied
    `goal` and optional S/O/K(t)/5W1H overrides), carried forward
    unmodified -- nothing inferred, nothing defaulted beyond what CLE's
    own API already defaults."""

    observation_id: str
    text: str
    goal: str
    metadata: dict[str, Any]
    timestamp_ns: int
    provenance: tuple[str, ...]
    state_hash: str
    five_w1h_overrides: FiveW1HOverrides | None
    sok_overrides: SOKOverrides | None


def extract_grounding_context(
    observation: HEXTObservation,
    goal: str,
    *,
    five_w1h_overrides: FiveW1HOverrides | None = None,
    sok_overrides: SOKOverrides | None = None,
) -> GroundingContext | QuarantineReason:
    """Extract only what `observation` actually carries. Returns
    `QuarantineReason` under the same conditions `validate_observation`
    already quarantines for -- no additional validation is invented here.
    """
    validated = validate_observation(observation)
    if isinstance(validated, QuarantineReason):
        return validated

    return GroundingContext(
        observation_id=validated.observation_id,
        text=validated.text,
        goal=goal,
        metadata=dict(validated.metadata),
        timestamp_ns=validated.timestamp_ns,
        provenance=validated.provenance,
        state_hash=validated.content_hash,
        five_w1h_overrides=five_w1h_overrides,
        sok_overrides=sok_overrides,
    )


@dataclass(frozen=True, slots=True)
class GroundedObservation:
    """CLE's grounding result, tied back to the source observation's own
    identity/provenance/state_hash/timestamp -- distinct from, and never
    merged with, `meaning_mapper.measurement.meaning_measurement.
    MeaningMeasurement`. An Observation may be independently measured
    (`pipeline.process` -> `MeaningMeasurement`) and/or grounded (this),
    keyed by the same `observation_id`; neither is derived from the other.
    """

    observation_id: str
    provenance: tuple[str, ...]
    state_hash: str
    timestamp_ns: int
    grounded: GroundResult


def ground_observation(
    client: CLEClient,
    observation: HEXTObservation,
    goal: str,
    *,
    five_w1h_overrides: FiveW1HOverrides | None = None,
    sok_overrides: SOKOverrides | None = None,
) -> GroundedObservation | QuarantineReason:
    """Extract -> `POST /ground` -> wrap with the source observation's
    identity. Propagates whatever `client.ground()` raises
    (`CLEUnreachableError`/`CLEHTTPError`/`CLESchemaError`) unchanged --
    those are already-typed CLE failures this function does not hide,
    reinterpret, or convert into a `QuarantineReason` (quarantine is
    reserved for the observation itself being unusable, not for CLE being
    unreachable or erroring)."""
    context = extract_grounding_context(
        observation, goal, five_w1h_overrides=five_w1h_overrides, sok_overrides=sok_overrides
    )
    if isinstance(context, QuarantineReason):
        return context

    grounded = client.ground(
        context.text,
        context.goal,
        five_w1h_overrides=context.five_w1h_overrides,
        sok_overrides=context.sok_overrides,
    )
    return GroundedObservation(
        observation_id=context.observation_id,
        provenance=context.provenance,
        state_hash=context.state_hash,
        timestamp_ns=context.timestamp_ns,
        grounded=grounded,
    )


__all__ = [
    "GroundedObservation",
    "GroundingContext",
    "extract_grounding_context",
    "ground_observation",
]
