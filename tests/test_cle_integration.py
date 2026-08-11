"""Live integration test against a real CLE subprocess (see conftest.py's
`live_cle`/`cle_client` fixtures) -- proves the adapter actually works
against the real service, not just against a mocked transport."""

from __future__ import annotations

import pytest

from factories import make_hext_observation
from meaning_mapper.cle.client import CLEClient
from meaning_mapper.cle.errors import CLEHTTPError
from meaning_mapper.cle.grounding import GroundedObservation, ground_observation
from meaning_mapper.cle.models import ConceptInput, FiniteCategoryInput, Morphism
from meaning_mapper.errors import QuarantineReason
from meaning_mapper.pipeline import MeaningMapperPipeline


def test_ground_against_real_cle(cle_client: CLEClient) -> None:
    result = cle_client.ground("test prompt for meaning-mapper CLE adapter", "test goal")
    assert result.semantic_state.prompt == "test prompt for meaning-mapper CLE adapter"
    assert result.lift.concept_id.startswith("concept:")


def test_lift_with_measurement_shaped_point_against_real_cle(cle_client: CLEClient) -> None:
    """The schema-compatibility fact from Phase 1: a `MeaningMeasurement.theta`
    is a valid single-point `ConceptInput`. This proves that shape is
    actually accepted by the real CLE service, not just structurally
    plausible on paper."""
    measurement_shaped_point = ConceptInput(states=((0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8),))
    result = cle_client.lift(measurement_shaped_point)
    assert result.concept_id.startswith("concept:")
    assert result.proof.functor_axioms_satisfied is True


def test_health_against_real_cle(cle_client: CLEClient) -> None:
    health = cle_client.health()
    assert health["status"] == "ok"
    assert health["service"] == "cle"


def test_ground_observation_against_real_cle(cle_client: CLEClient) -> None:
    """Phase 3, end to end, real HEXT Observation -> real CLE: the actual
    completion criterion, not a mocked stand-in for it."""
    observation = make_hext_observation(
        observation_id="obs-integration-0001",
        text="軌跡が不安定なので安定化してほしい。",
        metadata={"lang": "ja"},
    )
    result = ground_observation(cle_client, observation, goal="stabilize trajectory")

    assert isinstance(result, GroundedObservation)
    assert result.observation_id == "obs-integration-0001"
    assert result.grounded.semantic_state.prompt == "軌跡が不安定なので安定化してほしい。"
    assert result.grounded.lift.concept_id.startswith("concept:")


def test_ground_observation_quarantines_without_reaching_real_cle(cle_client: CLEClient) -> None:
    result = ground_observation(cle_client, {"object": {}}, goal="g")
    assert isinstance(result, QuarantineReason)


def test_real_measurement_theta_lifts_against_real_cle(cle_client: CLEClient) -> None:
    """Item 8's actual completion proof: the real, unmodified measurement
    pipeline (Stage 1-8, untouched by this session's work) produces a real
    MeaningMeasurement; ConceptInput.from_measurement reads only its
    .theta; the real CLE service accepts it at /lift. Two independently
    real systems, connected by one explicit, narrow, named conversion."""
    observation = make_hext_observation(
        observation_id="obs-pipeline-to-cle-0001",
        text="a real observation flowing through the real measurement pipeline",
    )
    measurement_result = MeaningMapperPipeline().process(observation)
    assert measurement_result.is_valid
    assert measurement_result.measurement is not None

    concept = ConceptInput.from_measurement(measurement_result.measurement)
    lift_result = cle_client.lift(concept)

    assert lift_result.concept_id.startswith("concept:")
    assert lift_result.proof.functor_axioms_satisfied is True


def test_pullback_against_real_cle(cle_client: CLEClient) -> None:
    category = FiniteCategoryInput(
        objects=("a",), morphisms=(Morphism(name="id_a", source="a", target="a"),)
    )
    result = cle_client.pullback(category, category, category)
    assert result.shared_morphisms  # identical categories share at least the identity morphism


def test_compress_against_real_cle(cle_client: CLEClient) -> None:
    result = cle_client.compress("raw context text", ["m1", "m2"])
    assert result.raw_size > 0
    assert isinstance(result.meets_target, bool)


def test_recover_against_real_cle_returns_503_without_configured_recovery_engine(
    cle_client: CLEClient,
) -> None:
    """Confirms, live, what test_cle_client.py's mocked equivalent only
    simulated: the real default CLE app instance has no recovery_engine
    wired (categorical-lift-engine's own composition-root convention,
    unchanged by this session), so /recover genuinely 503s today."""
    point = ConceptInput(states=((0.0,),))
    with pytest.raises(CLEHTTPError) as exc_info:
        cle_client.recover(point, point, point)
    assert exc_info.value.status_code == 503
