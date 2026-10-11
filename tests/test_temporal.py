"""Time in the measurement: the opt-in time-aware discontinuity guard, and the declared
temporal context (T06 ``time_frame``) that is carried through but never measured."""

from __future__ import annotations

import math

import pytest
from tests.factories import make_hext_observation

from meaning_mapper.errors import QuarantineReason, QuarantineStage
from meaning_mapper.measurement.meaning_measurement import MeaningMeasurement
from meaning_mapper.pipeline import map_observation
from meaning_mapper.topology.topological_consistency import check_discontinuity_over_time
from meaning_mapper.validation.observation_validation import validate_observation

NS = 1_000_000_000

#: the example narrative: the subject left the school in spring 2004, the story was
#: heard in September 2026, the school was founded in 1890.
TIME_FRAME = {
    "absolute": "2026-09",
    "actor": {"text": "2004年の春", "from": "2004-03", "to": "2004-05"},
    "historical": {"text": "1890年", "year": 1890},
    "relative": {"actor_to_observation_years": 22, "historical_to_actor_years": 114},
}


# ---- the guard, as a pure function ------------------------------------------------------------


def test_time_guard_is_a_noop_without_previous_theta() -> None:
    assert (
        check_discontinuity_over_time(
            (0.0,), None, timestamp_ns=NS, previous_timestamp_ns=0, rate_max=1.0
        )
        is None
    )


def test_time_guard_quarantines_a_dimension_mismatch() -> None:
    result = check_discontinuity_over_time(
        (0.0, 0.0), (0.0,), timestamp_ns=NS, previous_timestamp_ns=0, rate_max=1.0
    )
    assert isinstance(result, QuarantineReason)
    assert "dimension" in result.detail


def test_time_guard_quarantines_observations_out_of_time_order() -> None:
    result = check_discontinuity_over_time(
        (0.0,), (0.0,), timestamp_ns=0, previous_timestamp_ns=NS, rate_max=1.0, observation_id="o"
    )
    assert isinstance(result, QuarantineReason)
    assert result.stage is QuarantineStage.SEMANTIC_PROJECTION
    assert result.observation_id == "o"
    assert "not in time order" in result.detail


def test_time_guard_falls_back_to_displacement_when_no_time_elapsed() -> None:
    same_tick = {"timestamp_ns": NS, "previous_timestamp_ns": NS, "rate_max": 1.0}
    assert check_discontinuity_over_time((1.0,), (0.0,), delta_max=5.0, **same_tick) is None
    result = check_discontinuity_over_time((9.0,), (0.0,), delta_max=5.0, **same_tick)
    assert isinstance(result, QuarantineReason)
    assert "discontinuous jump" in result.detail  # the displacement rule's own message


def test_the_same_jump_is_judged_by_how_long_it_took() -> None:
    jump = {"theta": (100.0,), "previous_theta": (0.0,), "rate_max": 1.0}
    slow = check_discontinuity_over_time(
        timestamp_ns=1_000 * NS,
        previous_timestamp_ns=0,
        **jump,  # 100 over 1000 s
    )
    fast = check_discontinuity_over_time(
        timestamp_ns=10 * NS,
        previous_timestamp_ns=0,
        **jump,  # 100 over 10 s
    )
    assert slow is None
    assert isinstance(fast, QuarantineReason)
    assert "discontinuous rate" in fast.detail


# ---- the guard, through the pipeline ----------------------------------------------------------


def _baseline() -> MeaningMeasurement:
    result = map_observation(make_hext_observation())
    assert result.measurement is not None
    return result.measurement


def test_previous_timestamp_alone_keeps_the_rfc_displacement_rule() -> None:
    base = _baseline()
    far = tuple(x + 10_000.0 for x in base.theta)
    result = map_observation(
        make_hext_observation(),
        previous_theta=far,
        previous_timestamp_ns=base.timestamp_ns - 10**6 * NS,  # a million seconds earlier
    )
    assert result.is_quarantined  # no rate_max given -> the displacement rule applies


def test_time_aware_guard_accepts_a_large_jump_across_a_large_gap() -> None:
    base = _baseline()
    far = tuple(x + 10_000.0 for x in base.theta)
    gap_ns = 10**9 * NS  # ~31 years
    accepted = map_observation(
        make_hext_observation(),
        previous_theta=far,
        previous_timestamp_ns=base.timestamp_ns - gap_ns,
        discontinuity_rate_max=1.0,
    )
    rejected = map_observation(
        make_hext_observation(),
        previous_theta=far,
        previous_timestamp_ns=base.timestamp_ns - NS,  # one second earlier
        discontinuity_rate_max=1.0,
    )
    assert accepted.is_valid
    assert rejected.is_quarantined


# ---- the declared temporal context ------------------------------------------------------------


def test_temporal_context_is_carried_onto_the_measurement() -> None:
    result = map_observation(make_hext_observation(metadata={"time_frame": TIME_FRAME}))
    assert result.measurement is not None
    assert result.measurement.temporal_context == TIME_FRAME
    assert result.measurement.as_dict()["temporal_context"] == TIME_FRAME


def test_temporal_context_is_never_measured() -> None:
    plain = map_observation(make_hext_observation(metadata={"k": "v"})).measurement
    framed = map_observation(
        make_hext_observation(metadata={"k": "v", "time_frame": TIME_FRAME})
    ).measurement
    assert plain is not None and framed is not None
    assert framed.theta == plain.theta
    assert framed.sigma == plain.sigma
    assert framed.density == plain.density
    assert framed.measurement_id == plain.measurement_id
    assert framed.provenance_hash != plain.provenance_hash  # but it is integrity-covered


def test_without_a_temporal_context_the_measurement_is_exactly_what_it_was() -> None:
    measurement = _baseline()
    assert measurement.temporal_context is None
    assert "temporal_context" not in measurement.as_dict()


def test_other_metadata_still_reaches_the_features() -> None:
    a = map_observation(make_hext_observation(metadata={"k": "a"})).measurement
    b = map_observation(make_hext_observation(metadata={"k": "b"})).measurement
    assert a is not None and b is not None
    assert a.theta != b.theta


def test_validation_keeps_metadata_whole_for_consumers_that_forward_it() -> None:
    validated = validate_observation(make_hext_observation(metadata={"time_frame": TIME_FRAME}))
    assert not isinstance(validated, QuarantineReason)
    assert validated.metadata == {"time_frame": TIME_FRAME}  # cle.grounding forwards this
    assert validated.temporal_context == TIME_FRAME


def test_the_measurement_owns_a_copy_of_the_temporal_context() -> None:
    frame = {"actor": {"year": 2004}}
    measurement = map_observation(make_hext_observation(metadata={"time_frame": frame})).measurement
    assert measurement is not None
    frame["actor"]["year"] = 1999  # the caller mutates its own object afterwards
    assert measurement.temporal_context == {"actor": {"year": 2004}}
    exported = measurement.as_dict()["temporal_context"]
    exported["actor"]["year"] = 1  # ... and so does a consumer of the export
    assert measurement.temporal_context == {"actor": {"year": 2004}}


def test_a_measurement_with_a_temporal_context_is_still_hashable() -> None:
    measurement = map_observation(
        make_hext_observation(metadata={"time_frame": TIME_FRAME})
    ).measurement
    assert measurement is not None
    assert isinstance(hash(measurement), int)


@pytest.mark.parametrize(
    ("bad", "fragment"),
    [
        ("2004", "JSON object"),
        (["2004"], "JSON object"),
        ({1: "x"}, "JSON object"),
        ({"actor": math.nan}, "finite JSON values"),
        ({"actor": object()}, "finite JSON values"),
    ],
)
def test_a_malformed_temporal_context_is_quarantined(bad: object, fragment: str) -> None:
    result = map_observation(make_hext_observation(metadata={"time_frame": bad}))
    assert result.is_quarantined
    assert result.quarantine is not None
    assert result.quarantine.stage is QuarantineStage.VALIDATION
    assert result.quarantine.observation_id == "obs-0000000000000001"
    assert fragment in result.quarantine.detail
