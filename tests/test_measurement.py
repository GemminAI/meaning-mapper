from __future__ import annotations

import pytest

from meaning_mapper.errors import InvariantError
from meaning_mapper.measurement.meaning_measurement import MeaningMeasurement


def _valid_measurement() -> MeaningMeasurement:
    return MeaningMeasurement(
        observation_id="obs-1",
        frame_id="meaning-mapper.default",
        theta=(1.0, 2.0),
        sigma=((1.0, 0.0), (0.0, 1.0)),
        timestamp_ns=123,
        density=0.5,
        provenance=("meaning-mapper@2.0.0",),
    )


def test_valid_measurement_validates_cleanly() -> None:
    _valid_measurement().validate()  # must not raise


def test_dimension_property() -> None:
    assert _valid_measurement().dimension == 2


def test_empty_theta_raises() -> None:
    measurement = MeaningMeasurement(
        observation_id="obs-1", frame_id="f", theta=(), sigma=(), timestamp_ns=1, density=0.0
    )
    with pytest.raises(InvariantError, match="non-empty"):
        measurement.validate()


def test_non_square_sigma_raises() -> None:
    measurement = MeaningMeasurement(
        observation_id="obs-1",
        frame_id="f",
        theta=(1.0, 2.0),
        sigma=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        timestamp_ns=1,
        density=0.0,
    )
    with pytest.raises(InvariantError, match="square"):
        measurement.validate()


def test_non_spd_sigma_raises() -> None:
    measurement = MeaningMeasurement(
        observation_id="obs-1",
        frame_id="f",
        theta=(1.0, 2.0),
        sigma=((1.0, 2.0), (2.0, 1.0)),
        timestamp_ns=1,
        density=0.0,
    )
    with pytest.raises(InvariantError, match="positive-definite"):
        measurement.validate()


def test_density_out_of_range_raises() -> None:
    measurement = MeaningMeasurement(
        observation_id="obs-1",
        frame_id="f",
        theta=(1.0,),
        sigma=((1.0,),),
        timestamp_ns=1,
        density=1.5,
    )
    with pytest.raises(InvariantError, match=r"\[0, 1\]"):
        measurement.validate()


def test_as_dict_matches_msr_structural_port_field_names() -> None:
    payload = _valid_measurement().as_dict()
    assert set(payload) == {
        "measurement_id",
        "observation_id",
        "frame_id",
        "theta",
        "sigma",
        "timestamp_ns",
        "density",
        "provenance",
        "provenance_hash",
    }
    assert payload["theta"] == [1.0, 2.0]
    assert payload["sigma"] == [[1.0, 0.0], [0.0, 1.0]]
    assert payload["density"] == 0.5
    assert payload["provenance"] == ["meaning-mapper@2.0.0"]
    assert payload["measurement_id"] == _valid_measurement().measurement_id
    assert payload["provenance_hash"] == _valid_measurement().provenance_hash


def test_default_provenance_is_empty_tuple() -> None:
    measurement = MeaningMeasurement(
        observation_id="obs-1",
        frame_id="f",
        theta=(1.0,),
        sigma=((1.0,),),
        timestamp_ns=1,
        density=0.0,
    )
    assert measurement.provenance == ()


def test_measurement_id_is_deterministic_uuid5() -> None:
    first = _valid_measurement()
    second = _valid_measurement()
    assert first.measurement_id == second.measurement_id
    assert first.measurement_id  # non-empty


def test_measurement_id_changes_with_inputs() -> None:
    base = _valid_measurement()
    different = MeaningMeasurement(
        observation_id="obs-2",
        frame_id="meaning-mapper.default",
        theta=(1.0, 2.0),
        sigma=((1.0, 0.0), (0.0, 1.0)),
        timestamp_ns=123,
        density=0.5,
    )
    assert base.measurement_id != different.measurement_id


def test_provenance_hash_is_deterministic_and_hex() -> None:
    first = _valid_measurement()
    second = _valid_measurement()
    assert first.provenance_hash == second.provenance_hash
    assert len(first.provenance_hash) == 64
    int(first.provenance_hash, 16)  # must not raise: valid hex


def test_theta_and_sigma_are_defensively_frozen() -> None:
    measurement = MeaningMeasurement(
        observation_id="obs-1",
        frame_id="f",
        theta=[1.0, 2.0],  # type: ignore[arg-type]
        sigma=[[1.0, 0.0], [0.0, 1.0]],  # type: ignore[arg-type]
        timestamp_ns=1,
        density=0.0,
    )
    assert measurement.theta == (1.0, 2.0)
    assert measurement.sigma == ((1.0, 0.0), (0.0, 1.0))
    assert isinstance(measurement.theta, tuple)
    assert isinstance(measurement.sigma, tuple)
