"""Request/response shapes for CLE's HTTP surface, verified live against
`categorical-lift-engine`'s running `/openapi.json` (2026-08-12) --
field-for-field structural mirror, not an import. Meaning Mapper does not
depend on `cle`.

Plain `@dataclass(frozen=True, slots=True)`, matching this repo's own
convention (`meaning_mapper.types`, `meaning_mapper.measurement`) rather
than introducing pydantic for one adapter.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from meaning_mapper._linalg import Vector
from meaning_mapper.cle.errors import CLESchemaError
from meaning_mapper.measurement.meaning_measurement import MeaningMeasurement


def _require(body: dict[str, Any], key: str) -> Any:
    if key not in body:
        raise CLESchemaError(f"missing required field {key!r}", body)
    return body[key]


# --- /ground --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FiveW1HOverrides:
    who: str | None = None
    what: str | None = None
    when: str | None = None
    where: str | None = None
    why: str | None = None
    how: str | None = None

    def to_payload(self) -> dict[str, str]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass(frozen=True, slots=True)
class SOKOverrides:
    subject: str | None = None
    observer: str | None = None
    knowledge_reference: str | None = None

    def to_payload(self) -> dict[str, str]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass(frozen=True, slots=True)
class FiveW1HField:
    value: str
    source: str

    @classmethod
    def from_payload(cls, body: dict[str, Any]) -> FiveW1HField:
        return cls(value=_require(body, "value"), source=_require(body, "source"))


@dataclass(frozen=True, slots=True)
class FiveW1H:
    who: FiveW1HField
    what: FiveW1HField
    when: FiveW1HField
    where: FiveW1HField
    why: FiveW1HField
    how: FiveW1HField

    @classmethod
    def from_payload(cls, body: dict[str, Any]) -> FiveW1H:
        return cls(
            **{name: FiveW1HField.from_payload(_require(body, name)) for name in FIVE_W1H_FIELDS}
        )


FIVE_W1H_FIELDS = ("who", "what", "when", "where", "why", "how")


@dataclass(frozen=True, slots=True)
class SOK:
    subject: str
    subject_source: str
    observer: str
    observer_source: str
    knowledge_reference: str
    knowledge_reference_source: str

    @classmethod
    def from_payload(cls, body: dict[str, Any]) -> SOK:
        return cls(**{name: _require(body, name) for name in _SOK_FIELDS})


_SOK_FIELDS = (
    "subject",
    "subject_source",
    "observer",
    "observer_source",
    "knowledge_reference",
    "knowledge_reference_source",
)


@dataclass(frozen=True, slots=True)
class GroundedState:
    """CLE's Semantic Grounding output (`GroundResponse.semantic_state`)."""

    prompt: str
    goal: str
    five_w1h: FiveW1H
    sok: SOK
    fingerprint: tuple[str, ...]
    goal_fingerprint: tuple[str, ...]
    subject_fingerprint: tuple[str, ...]
    observer_fingerprint: tuple[str, ...]
    knowledge_fingerprint: tuple[str, ...]

    @classmethod
    def from_payload(cls, body: dict[str, Any]) -> GroundedState:
        return cls(
            prompt=_require(body, "prompt"),
            goal=_require(body, "goal"),
            five_w1h=FiveW1H.from_payload(_require(body, "five_w1h")),
            sok=SOK.from_payload(_require(body, "sok")),
            fingerprint=tuple(_require(body, "fingerprint")),
            goal_fingerprint=tuple(_require(body, "goal_fingerprint")),
            subject_fingerprint=tuple(_require(body, "subject_fingerprint")),
            observer_fingerprint=tuple(_require(body, "observer_fingerprint")),
            knowledge_fingerprint=tuple(_require(body, "knowledge_fingerprint")),
        )


# --- shared: /lift, /recover point clouds ----------------------------------


@dataclass(frozen=True, slots=True)
class ConceptInput:
    """A point cloud: one `theta` per point. Matches
    `MeaningMeasurement.theta`'s shape (`meaning_mapper._linalg.Vector`) --
    an MM measurement is a single-point `ConceptInput`, not a conversion."""

    states: tuple[Vector, ...]

    def to_payload(self) -> dict[str, Any]:
        return {"states": [{"theta": list(theta)} for theta in self.states]}

    @classmethod
    def from_measurement(cls, measurement: MeaningMeasurement) -> ConceptInput:
        """A `MeaningMeasurement` is one position-plus-uncertainty reading;
        `.theta` is already the exact `Vector` shape a single-point
        `ConceptInput` needs. This reads `.theta` only and does not merge,
        wrap, or otherwise conflate `MeaningMeasurement` with any CLE type
        -- `.sigma`/`.density`/`.provenance` are not carried into CLE by
        this method, the same way `to_payload()` never reaches back into a
        `MeaningMeasurement` either."""
        return cls(states=(measurement.theta,))


# --- /lift ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InvariantSignature:
    betti_0: int
    betti_1: int
    betti_2: int
    euler_characteristic: int

    @classmethod
    def from_payload(cls, body: dict[str, Any]) -> InvariantSignature:
        return cls(
            betti_0=_require(body, "betti_0"),
            betti_1=_require(body, "betti_1"),
            betti_2=_require(body, "betti_2"),
            euler_characteristic=_require(body, "euler_characteristic"),
        )


@dataclass(frozen=True, slots=True)
class ProofCertificate:
    is_valid: bool
    boundary_condition_verified: bool
    functor_axioms_satisfied: bool
    proof_trace: tuple[str, ...]

    @classmethod
    def from_payload(cls, body: dict[str, Any]) -> ProofCertificate:
        return cls(
            is_valid=_require(body, "is_valid"),
            boundary_condition_verified=_require(body, "boundary_condition_verified"),
            functor_axioms_satisfied=_require(body, "functor_axioms_satisfied"),
            proof_trace=tuple(_require(body, "proof_trace")),
        )


@dataclass(frozen=True, slots=True)
class LiftResult:
    concept_id: str
    normalized_hash: str
    morphisms: tuple[tuple[str, str, str], ...]
    pullback_limit: dict[str, Any]
    pushout_colimit: dict[str, Any]
    invariants: InvariantSignature
    compression_ratio: float
    semantic_closure: dict[str, Any]
    proof: ProofCertificate

    @classmethod
    def from_payload(cls, body: dict[str, Any]) -> LiftResult:
        return cls(
            concept_id=_require(body, "concept_id"),
            normalized_hash=_require(body, "normalized_hash"),
            morphisms=tuple(tuple(m) for m in _require(body, "morphisms")),
            pullback_limit=_require(body, "pullback_limit"),
            pushout_colimit=_require(body, "pushout_colimit"),
            invariants=InvariantSignature.from_payload(_require(body, "invariants")),
            compression_ratio=_require(body, "compression_ratio"),
            semantic_closure=_require(body, "semantic_closure"),
            proof=ProofCertificate.from_payload(_require(body, "proof")),
        )


@dataclass(frozen=True, slots=True)
class GroundResult:
    """`GroundResponse`: both halves CLE returns from `POST /ground`."""

    semantic_state: GroundedState
    lift: LiftResult

    @classmethod
    def from_payload(cls, body: dict[str, Any]) -> GroundResult:
        return cls(
            semantic_state=GroundedState.from_payload(_require(body, "semantic_state")),
            lift=LiftResult.from_payload(_require(body, "lift")),
        )


# --- /pullback ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Morphism:
    name: str
    source: str
    target: str

    def to_payload(self) -> dict[str, str]:
        return {"name": self.name, "source": self.source, "target": self.target}

    @classmethod
    def from_payload(cls, body: dict[str, Any]) -> Morphism:
        return cls(
            name=_require(body, "name"),
            source=_require(body, "source"),
            target=_require(body, "target"),
        )


@dataclass(frozen=True, slots=True)
class CompositionEntry:
    g: str
    f: str
    h: str

    def to_payload(self) -> dict[str, str]:
        return {"g": self.g, "f": self.f, "h": self.h}


@dataclass(frozen=True, slots=True)
class FiniteCategoryInput:
    objects: tuple[str, ...]
    morphisms: tuple[Morphism, ...]
    composition: tuple[CompositionEntry, ...] = field(default_factory=tuple)

    def to_payload(self) -> dict[str, Any]:
        return {
            "objects": list(self.objects),
            "morphisms": [m.to_payload() for m in self.morphisms],
            "composition": [c.to_payload() for c in self.composition],
        }


@dataclass(frozen=True, slots=True)
class PullbackResult:
    shared_morphisms: tuple[Morphism, ...]

    @classmethod
    def from_payload(cls, body: dict[str, Any]) -> PullbackResult:
        return cls(
            shared_morphisms=tuple(
                Morphism.from_payload(m) for m in _require(body, "shared_morphisms")
            )
        )


# --- /recover -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RecoveredContext:
    recovered_state_id: str
    reconstructed_closure: dict[str, Any]
    three_view_discrepancy: float
    converged: bool

    @classmethod
    def from_payload(cls, body: dict[str, Any]) -> RecoveredContext:
        return cls(
            recovered_state_id=_require(body, "recovered_state_id"),
            reconstructed_closure=_require(body, "reconstructed_closure"),
            three_view_discrepancy=_require(body, "three_view_discrepancy"),
            converged=_require(body, "converged"),
        )


# --- /compress ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CompressionResult:
    raw_size: int
    lifted_size: int
    ratio: float
    meets_target: bool

    @classmethod
    def from_payload(cls, body: dict[str, Any]) -> CompressionResult:
        return cls(
            **{
                name: _require(body, name)
                for name in ("raw_size", "lifted_size", "ratio", "meets_target")
            }
        )


__all__ = [
    "SOK",
    "CompositionEntry",
    "CompressionResult",
    "ConceptInput",
    "FiniteCategoryInput",
    "FiveW1H",
    "FiveW1HField",
    "FiveW1HOverrides",
    "GroundResult",
    "GroundedState",
    "InvariantSignature",
    "LiftResult",
    "Morphism",
    "ProofCertificate",
    "PullbackResult",
    "RecoveredContext",
    "SOKOverrides",
]
