"""Window rows become theta, sigma, and density in a caller-supplied frame."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from meaning_mapper.density.density_estimation import compute_semantic_density
from meaning_mapper.envelope import build_measurement_artifact
from meaning_mapper.window import (
    WindowFrame,
    WindowMeasureError,
    frame_content_id,
    measure_window,
    window_rows,
)

_VENDOR = Path(__file__).resolve().parent / "vendor_contracts"


def _frame(
    *,
    mu: Any = None,
    basis: Any = None,
    sigma0: Any = None,
    frame_id: str | None = None,
) -> WindowFrame:
    held_mu = np.array([1.0, 1.0]) if mu is None else mu
    held_basis = np.array([[1.0, 1.0], [1.0, -1.0]]) if basis is None else basis
    held_sigma0 = np.array([[2.0, 0.0], [0.0, 2.0]]) if sigma0 is None else sigma0
    if frame_id is None:
        return WindowFrame(mu=held_mu, basis=held_basis, sigma0=held_sigma0)
    return WindowFrame(mu=held_mu, basis=held_basis, sigma0=held_sigma0, frame_id=frame_id)


def _rows() -> np.ndarray[Any, np.dtype[np.float64]]:
    return np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float64)


def _refuses(field: str, call: Callable[[], Any]) -> None:
    with pytest.raises(WindowMeasureError) as caught:
        call()
    assert caught.value.field == field


def test_a_hand_worked_window_matches_the_formula() -> None:
    rows = _rows()
    frame = _frame()
    sigma0 = np.array(frame.sigma0)
    whole = measure_window(rows, [{"start": 0, "length": 3}], frame)
    assert whole.theta.tobytes() == np.array([[5.0, -1.0]], dtype=np.float64).tobytes()
    assert whole.sigma.tobytes() == (sigma0 / 3).reshape(1, 2, 2).tobytes()
    assert whole.density[0] == compute_semantic_density(np.array([5.0, -1.0]))

    one = measure_window(rows, [{"start": 1, "length": 1}], frame)
    assert one.theta.tobytes() == np.array([[5.0, -1.0]], dtype=np.float64).tobytes()
    assert one.sigma[0].tobytes() == sigma0.tobytes()
    assert one.density[0] == compute_semantic_density(one.theta[0])

    split = measure_window(rows, [{"start": 0, "length": 2}, {"start": 2, "length": 1}], frame)
    expect = np.array([[3.0, -1.0], [9.0, -1.0]], dtype=np.float64)
    assert split.theta.tobytes() == expect.tobytes()
    assert split.sigma[0].tobytes() == (sigma0 / 2).tobytes()
    assert split.sigma[1].tobytes() == sigma0.tobytes()
    for index in range(2):
        assert split.density[index] == compute_semantic_density(split.theta[index])


def test_known_densities_are_one_and_zero() -> None:
    identity = np.eye(2)
    concentrated = measure_window(
        np.array([[3.0, 0.0]]),
        [{"start": 0, "length": 1}],
        _frame(mu=np.zeros(2), basis=identity, sigma0=identity),
    )
    spread = measure_window(
        np.array([[1.0, 1.0]]),
        [{"start": 0, "length": 1}],
        _frame(mu=np.zeros(2), basis=identity, sigma0=identity),
    )
    assert concentrated.density[0] == 1.0
    assert spread.density[0] == 0.0


def test_two_calls_match_byte_for_byte() -> None:
    rng = np.random.default_rng(0)
    rows = rng.standard_normal((48, 64))
    frame = _frame(
        mu=rows.mean(axis=0),
        basis=rng.standard_normal((8, 64)) / np.sqrt(64),
        sigma0=np.eye(8) * 1e-3,
    )
    points = [{"start": index, "length": 1} for index in range(48)]
    first = measure_window(rows, points, frame)
    second = measure_window(rows, points, frame)
    assert first.theta.tobytes() == second.theta.tobytes()
    assert first.sigma.tobytes() == second.sigma.tobytes()
    assert first.density.tobytes() == second.density.tobytes()


def test_an_omitted_frame_id_is_the_content_id_and_a_name_is_kept() -> None:
    mu = np.array([1.0, 2.0])
    basis = np.eye(2)
    sigma0 = np.eye(2) * 0.5
    frame = _frame(mu=mu, basis=basis, sigma0=sigma0)
    assert frame.frame_id == frame_content_id(mu, basis, sigma0)
    assert frame_content_id(mu, basis, sigma0) == frame_content_id(mu, basis, sigma0)
    named = _frame(mu=mu, basis=basis, sigma0=sigma0, frame_id="other")
    assert named.frame_id == "other"
    changed = mu.copy()
    changed[0] = 9.0
    assert frame_content_id(changed, basis, sigma0) != frame.frame_id
    wide = np.array([[1.0, 2.0, 3.0, 4.0]])
    assert frame_content_id(wide.reshape(4), np.eye(1), np.eye(1)) != frame_content_id(
        wide.reshape(1, 4), np.eye(1), np.eye(1)
    )
    fortran = np.array(basis, order="F")
    assert frame_content_id(mu, fortran, sigma0) == frame_content_id(mu, basis, sigma0)
    mu[0] = 9.0
    assert frame.mu[0] == 1.0


def test_the_frame_refuses_a_bad_input() -> None:
    _refuses("mu", lambda: _frame(mu=np.array([[1.0, 2.0]])))
    _refuses("mu", lambda: _frame(mu=np.array([])))
    _refuses("mu", lambda: _frame(mu=np.array([np.nan, 1.0])))
    _refuses("basis", lambda: _frame(basis=np.array([1.0, 0.0])))
    _refuses("basis", lambda: _frame(basis=np.ones((2, 3))))
    _refuses("basis", lambda: _frame(basis=np.array([[np.inf, 0.0], [0.0, 1.0]])))
    _refuses("sigma0", lambda: _frame(sigma0=np.ones((2, 3))))
    _refuses("sigma0", lambda: _frame(sigma0=np.array([[1.0, 1.0], [0.0, 1.0]])))
    _refuses("sigma0", lambda: _frame(sigma0=np.zeros((2, 2))))
    _refuses("frame_id", lambda: _frame(frame_id=""))
    _refuses("frame_id", lambda: WindowFrame(np.zeros(2), np.eye(2), np.eye(2), frame_id=1))  # type: ignore[arg-type]
    _refuses("mu", lambda: frame_content_id("no", np.eye(2), np.eye(2)))


def test_measure_window_refuses_a_bad_input() -> None:
    frame = _frame()
    rows = _rows()
    _refuses("rows", lambda: measure_window(rows[0], [{"start": 0, "length": 1}], frame))
    _refuses("rows", lambda: measure_window(np.zeros((0, 2)), [{"start": 0, "length": 1}], frame))
    _refuses(
        "rows",
        lambda: measure_window(np.array([[np.nan, 1.0]]), [{"start": 0, "length": 1}], frame),
    )
    _refuses(
        "dimension",
        lambda: measure_window(np.ones((2, 3)), [{"start": 0, "length": 1}], frame),
    )
    _refuses("points", lambda: measure_window(rows, ({"start": 0, "length": 1},), frame))  # type: ignore[arg-type]
    _refuses("points", lambda: measure_window(rows, [], frame))
    _refuses("points", lambda: measure_window(rows, ["row"], frame))  # type: ignore[list-item]
    _refuses("points", lambda: measure_window(rows, [{"start": True, "length": 1}], frame))
    _refuses("points", lambda: measure_window(rows, [{"start": 0, "length": 1.5}], frame))
    _refuses("points", lambda: measure_window(rows, [{"start": -1, "length": 1}], frame))
    _refuses("points", lambda: measure_window(rows, [{"start": 0, "length": 0}], frame))
    _refuses("points", lambda: measure_window(rows, [{"start": 2, "length": 2}], frame))
    huge = _frame(mu=np.zeros(2), basis=np.array([[1e308, 0.0]]), sigma0=np.array([[1.0]]))
    _refuses(
        "theta",
        lambda: measure_window(np.array([[1e308, 1e308]]), [{"start": 0, "length": 1}], huge),
    )


def _points_blob(
    values: np.ndarray[Any, np.dtype[np.float32]], *, raw: bytes | None = None
) -> tuple[dict[str, Any], dict[str, bytes]]:
    body = np.ascontiguousarray(values, dtype="<f4").tobytes() if raw is None else raw
    digest = hashlib.sha256(np.ascontiguousarray(values, dtype="<f4").tobytes()).hexdigest()
    uri = "blob:sha256:" + digest
    length, dimension = values.shape
    envelope = {
        "payload": {
            "window": {"length": int(length)},
            "dimension": int(dimension),
            "points": {
                "uri": uri,
                "sha256": digest,
                "dtype": "float32",
                "shape": [int(length), int(dimension)],
                "byte_order": "little",
                "order": "C",
            },
        }
    }
    return envelope, {uri: body}


def test_window_rows_reads_float32_and_checks_the_blob() -> None:
    values = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    envelope, blobs = _points_blob(values)
    got = window_rows(envelope, blobs)
    assert got.dtype == np.float64
    assert got.tobytes() == np.array(values, dtype=np.float64).tobytes()
    uri = envelope["payload"]["points"]["uri"]
    assert window_rows(envelope, {uri: bytearray(blobs[uri])}).tobytes() == got.tobytes()

    short = blobs[uri][:-1]
    _refuses("points", lambda: window_rows(envelope, {uri: short}))
    flipped = bytearray(blobs[uri])
    flipped[0] ^= 0x01
    _refuses("sha256", lambda: window_rows(envelope, {uri: bytes(flipped)}))
    _refuses("points", lambda: window_rows(envelope, {}))
    _refuses("points", lambda: window_rows(envelope, None))  # type: ignore[arg-type]


def test_window_rows_refuses_a_bad_envelope() -> None:
    values = np.array([[1.0, 2.0]], dtype=np.float32)
    envelope, blobs = _points_blob(values)
    points = envelope["payload"]["points"]
    _refuses("payload", lambda: window_rows({}, blobs))
    _refuses("length", lambda: window_rows({"payload": {"dimension": 2}}, blobs))
    _refuses("length", lambda: window_rows({"payload": {"window": "x", "dimension": 2}}, blobs))
    _refuses(
        "length",
        lambda: window_rows({"payload": {"window": {"length": True}, "dimension": 2}}, blobs),
    )
    _refuses(
        "dimension",
        lambda: window_rows({"payload": {"window": {"length": 1}, "dimension": -1}}, blobs),
    )
    _refuses(
        "shape",
        lambda: window_rows({"payload": {"window": {"length": 0}, "dimension": 2}}, blobs),
    )
    _refuses(
        "shape",
        lambda: window_rows({"payload": {"window": {"length": 1}, "dimension": 0}}, blobs),
    )
    held = json.loads(json.dumps(envelope))
    del held["payload"]["points"]
    _refuses("points", lambda: window_rows(held, blobs))
    for key, value, field in (
        ("dtype", "float64", "points"),
        ("byte_order", "big", "points"),
        ("order", "F", "points"),
        ("shape", [1, 3], "shape"),
        ("sha256", 1, "sha256"),
        ("uri", "blob:sha256:" + "0" * 64, "sha256"),
    ):
        broken = json.loads(json.dumps(envelope))
        broken["payload"]["points"][key] = value
        _refuses(field, lambda held=broken: window_rows(held, blobs))
    assert points["dtype"] == "float32"


def _seal(envelope: dict[str, Any], lookup: Mapping[str, Any]) -> dict[str, Any]:
    sealed = dict(envelope)
    raw = json.dumps({"envelope": envelope, "lookup": dict(lookup)}, sort_keys=True).encode()
    digest = hashlib.sha256(raw).hexdigest()
    sealed["content_id"] = "cnt:" + digest
    sealed["artifact_id"] = "art:" + digest
    return sealed


def _validator() -> Any:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012

    blob = json.loads((_VENDOR / "common" / "blob.schema.json").read_text(encoding="utf-8"))
    schema = json.loads((_VENDOR / "meaning-measurement.schema.json").read_text(encoding="utf-8"))
    registry = Registry().with_resource(blob["$id"], Resource.from_contents(blob, DRAFT202012))
    return Draft202012Validator(schema, registry=registry)


def test_a_measured_window_seals_an_envelope_the_schema_accepts() -> None:
    values = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float32)
    described, blobs = _points_blob(values)
    rows = window_rows(described, blobs)
    frame = _frame()
    measured = measure_window(rows, [{"start": 0, "length": 3}], frame)
    window = {
        "artifact_id": "art:" + "a" * 64,
        "content_id": "cnt:" + "a" * 64,
        "payload_schema": {"id": "msr.trajectory-window", "version": "0.10.0"},
        "producer": {"name": "nvs-runtime", "version": "1.0.0", "build": "w"},
        "session_id": "ses:" + "e" * 64,
        "observation_id": "obs:" + "f" * 64,
        "space_id": "space-1",
        "seq": 2,
        "produced_at": "2026-11-21T00:00:00Z",
        "parents": [
            {"role": "source_trajectory", "ordered": False, "artifact_ids": ["art:" + "1" * 64]}
        ],
        "payload": described["payload"],
    }
    artifact = build_measurement_artifact(
        window,
        None,
        str(frame.frame_id),
        [{"start": 0, "length": 3}],
        measured.theta,
        measured.sigma,
        measured.density,
        "mm-window",
        _seal,
    )
    assert list(_validator().iter_errors(artifact.envelope["payload"])) == []
    assert artifact.envelope["payload"]["frame_id"] == frame.frame_id
