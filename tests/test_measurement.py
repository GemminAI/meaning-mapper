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
        provenance=("meaning-mapper@2.0.0",),
    )


def test_valid_measurement_validates_cleanly() -> None:
    _valid_measurement().validate()  # must not raise


def test_dimension_property() -> None:
    assert _valid_measurement().dimension == 2


def test_empty_theta_raises() -> None:
    measurement = MeaningMeasurement(
        observation_id="obs-1", frame_id="f", theta=(), sigma=(), timestamp_ns=1
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
    )
    with pytest.raises(InvariantError, match="positive-definite"):
        measurement.validate()


def test_as_dict_matches_msr_structural_port_field_names() -> None:
    payload = _valid_measurement().as_dict()
    assert set(payload) == {
        "observation_id",
        "frame_id",
        "theta",
        "sigma",
        "timestamp_ns",
        "provenance",
    }
    assert payload["theta"] == [1.0, 2.0]
    assert payload["sigma"] == [[1.0, 0.0], [0.0, 1.0]]
    assert payload["provenance"] == ["meaning-mapper@2.0.0"]


def test_default_provenance_is_empty_tuple() -> None:
    measurement = MeaningMeasurement(
        observation_id="obs-1", frame_id="f", theta=(1.0,), sigma=((1.0,),), timestamp_ns=1
    )
    assert measurement.provenance == ()
