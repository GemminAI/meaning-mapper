"""cle.models: request payload building and response parsing, including
the CLESchemaError path for a response missing a required field."""

from __future__ import annotations

import pytest

from meaning_mapper.cle.errors import CLESchemaError
from meaning_mapper.cle.models import (
    SOK,
    CompositionEntry,
    CompressionResult,
    ConceptInput,
    FiniteCategoryInput,
    FiveW1H,
    FiveW1HField,
    FiveW1HOverrides,
    GroundedState,
    GroundResult,
    InvariantSignature,
    LiftResult,
    Morphism,
    ProofCertificate,
    PullbackResult,
    RecoveredContext,
    SOKOverrides,
)
from meaning_mapper.measurement.meaning_measurement import MeaningMeasurement


def test_five_w1h_overrides_to_payload_drops_none() -> None:
    overrides = FiveW1HOverrides(who="a", what=None)
    assert overrides.to_payload() == {"who": "a"}


def test_sok_overrides_to_payload_drops_none() -> None:
    overrides = SOKOverrides(subject="s", observer=None, knowledge_reference="k")
    assert overrides.to_payload() == {"subject": "s", "knowledge_reference": "k"}


def test_concept_input_to_payload() -> None:
    concept = ConceptInput(states=((1.0, 2.0), (3.0, 4.0)))
    assert concept.to_payload() == {"states": [{"theta": [1.0, 2.0]}, {"theta": [3.0, 4.0]}]}


def test_concept_input_from_measurement_reads_theta_only() -> None:
    """The explicit, named /lift <-> MeaningMeasurement.theta connection.
    Does not carry sigma/density/provenance -- ConceptInput has no fields
    for them, so there is nothing to accidentally conflate."""
    measurement = MeaningMeasurement(
        observation_id="obs-1",
        frame_id="frame-1",
        theta=(0.1, 0.2, 0.3),
        sigma=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        timestamp_ns=1_000,
        density=0.5,
        provenance=("meaning-mapper@2.2.0",),
    )
    concept = ConceptInput.from_measurement(measurement)
    assert concept.states == ((0.1, 0.2, 0.3),)


def test_finite_category_input_to_payload() -> None:
    category = FiniteCategoryInput(
        objects=("a", "b"),
        morphisms=(Morphism(name="id_a", source="a", target="a"),),
        composition=(CompositionEntry(g="id_a", f="id_a", h="id_a"),),
    )
    assert category.to_payload() == {
        "objects": ["a", "b"],
        "morphisms": [{"name": "id_a", "source": "a", "target": "a"}],
        "composition": [{"g": "id_a", "f": "id_a", "h": "id_a"}],
    }


_FIVE_W1H_FIELD_PAYLOAD = {"value": "v", "source": "explicit"}
_FIVE_W1H_PAYLOAD = {
    name: _FIVE_W1H_FIELD_PAYLOAD for name in ("who", "what", "when", "where", "why", "how")
}
_SOK_PAYLOAD = {
    "subject": "s",
    "subject_source": "explicit",
    "observer": "o",
    "observer_source": "derived",
    "knowledge_reference": "k",
    "knowledge_reference_source": "unspecified",
}


def test_grounded_state_from_payload() -> None:
    payload = {
        "prompt": "p",
        "goal": "g",
        "five_w1h": _FIVE_W1H_PAYLOAD,
        "sok": _SOK_PAYLOAD,
        "fingerprint": ["abc"],
        "goal_fingerprint": ["def"],
        "subject_fingerprint": ["ghi"],
        "observer_fingerprint": ["jkl"],
        "knowledge_fingerprint": ["mno"],
    }
    state = GroundedState.from_payload(payload)
    assert state.prompt == "p"
    assert state.five_w1h == FiveW1H(
        **{name: FiveW1HField(**_FIVE_W1H_FIELD_PAYLOAD) for name in _FIVE_W1H_PAYLOAD}
    )
    assert state.sok == SOK(**_SOK_PAYLOAD)
    assert state.fingerprint == ("abc",)


def test_grounded_state_from_payload_missing_field_raises_schema_error() -> None:
    with pytest.raises(CLESchemaError):
        GroundedState.from_payload({"prompt": "p"})


_LIFT_PAYLOAD = {
    "concept_id": "concept:abc",
    "normalized_hash": "normalized:def",
    "morphisms": [["v0", "v0", "identity"]],
    "pullback_limit": {"morphisms": []},
    "pushout_colimit": {"objects": [], "morphisms": []},
    "invariants": {"betti_0": 1, "betti_1": 0, "betti_2": 0, "euler_characteristic": 1},
    "compression_ratio": 2.5,
    "semantic_closure": {},
    "proof": {
        "is_valid": True,
        "boundary_condition_verified": True,
        "functor_axioms_satisfied": True,
        "proof_trace": ["ok"],
    },
}


def test_lift_result_from_payload() -> None:
    result = LiftResult.from_payload(_LIFT_PAYLOAD)
    assert result.concept_id == "concept:abc"
    assert result.morphisms == (("v0", "v0", "identity"),)
    assert result.invariants == InvariantSignature(
        betti_0=1, betti_1=0, betti_2=0, euler_characteristic=1
    )
    assert result.proof == ProofCertificate(
        is_valid=True,
        boundary_condition_verified=True,
        functor_axioms_satisfied=True,
        proof_trace=("ok",),
    )


def test_ground_result_from_payload() -> None:
    payload = {
        "semantic_state": {
            "prompt": "p",
            "goal": "g",
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
    result = GroundResult.from_payload(payload)
    assert result.semantic_state.prompt == "p"
    assert result.lift.concept_id == "concept:abc"


def test_pullback_result_from_payload() -> None:
    result = PullbackResult.from_payload(
        {"shared_morphisms": [{"name": "id_v0", "source": "v0", "target": "v0"}]}
    )
    assert result.shared_morphisms == (Morphism(name="id_v0", source="v0", target="v0"),)


def test_recovered_context_from_payload() -> None:
    result = RecoveredContext.from_payload(
        {
            "recovered_state_id": "recovered:abc",
            "reconstructed_closure": {"shared_morphisms": []},
            "three_view_discrepancy": 0.1,
            "converged": True,
        }
    )
    assert result.recovered_state_id == "recovered:abc"
    assert result.converged is True


def test_compression_result_from_payload() -> None:
    result = CompressionResult.from_payload(
        {"raw_size": 100, "lifted_size": 10, "ratio": 10.0, "meets_target": True}
    )
    assert result == CompressionResult(raw_size=100, lifted_size=10, ratio=10.0, meets_target=True)
