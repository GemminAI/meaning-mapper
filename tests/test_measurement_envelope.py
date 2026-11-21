"""The nvs.meaning-measurement envelope is assembled, not measured."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from meaning_mapper.envelope import (
    MeasurementInputError,
    build_measurement_artifact,
)
from meaning_mapper.envelope.build import _jcs
from meaning_mapper.version import __version__

_VENDOR = Path(__file__).resolve().parent / "vendor_contracts"
_CONTRACTS_PREFIX = "docs/architecture/contracts/"
_OBS = "art:" + "1" * 64
_WINDOW = "art:" + "a" * 64
_AXIS = "art:" + "b" * 64
_D = 2


def _seal(envelope: dict[str, Any], lookup: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(envelope)
    raw = json.dumps({"envelope": envelope, "lookup": lookup}, sort_keys=True).encode()
    digest = hashlib.sha256(raw).hexdigest()
    sealed["content_id"] = "cnt:" + digest
    sealed["artifact_id"] = "art:" + digest
    return sealed


def _window(
    *,
    length: int = 4,
    origin: int = 4,
    seq: int = 2,
    space_id: str | None = "space-1",
    producer: str = "nvs-runtime",
    schema: tuple[str, str] = ("msr.trajectory-window", "0.10.0"),
    parent: str = _OBS,
) -> dict[str, Any]:
    return {
        "artifact_id": _WINDOW,
        "content_id": "cnt:" + "a" * 64,
        "payload_schema": {"id": schema[0], "version": schema[1]},
        "producer": {"name": producer, "version": "1.0.0", "build": "w"},
        "session_id": "ses:" + "e" * 64,
        "observation_id": "obs:" + "f" * 64,
        "space_id": space_id,
        "seq": seq,
        "produced_at": "2026-11-21T00:00:00Z",
        "parents": [{"role": "source_trajectory", "ordered": False, "artifact_ids": [parent]}],
        "payload": {"window": {"length": length}, "origin": {"length": origin}},
    }


def _axis(
    *,
    n: int = 4,
    seq: int = 2,
    parent: str = _OBS,
    schema: tuple[str, str] = ("nvs.token-temporal", "0.1.0"),
    observation_id: str = "obs:" + "f" * 64,
) -> dict[str, Any]:
    return {
        "artifact_id": _AXIS,
        "content_id": "cnt:" + "b" * 64,
        "payload_schema": {"id": schema[0], "version": schema[1]},
        "producer": {"name": "sensos-inference", "version": "0.1.0", "build": "t"},
        "session_id": "ses:" + "e" * 64,
        "observation_id": observation_id,
        "seq": seq,
        "parents": [{"role": "source_observation", "ordered": False, "artifact_ids": [parent]}],
        "payload": {
            "segments": [
                {"origin": "input", "n": 3},
                "skip",
                {"origin": "generated", "n": n},
            ]
        },
    }


def _observation(
    artifact_id: str = _OBS,
    *,
    alignment: str | None = "decides-next/1",
    binding: bool = True,
) -> dict[str, Any]:
    if not binding:
        return {"artifact_id": artifact_id, "payload": {}}
    if alignment is None:
        return {"artifact_id": artifact_id}
    return {
        "artifact_id": artifact_id,
        "payload": {"binding": {"alignment": alignment}},
    }


def _values(n: int, d: int = _D) -> tuple[np.ndarray[Any, np.dtype[np.float64]], ...]:
    theta = np.zeros((n, d), dtype=np.float64)
    sigma = np.zeros((n, d, d), dtype=np.float64)
    for index in range(n):
        sigma[index] = np.eye(d)
    density = np.full(n, 0.5, dtype=np.float64)
    return theta, sigma, density


def _build(
    *,
    n: int = 1,
    axis: Mapping[str, Any] | None = None,
    window: Mapping[str, Any] | None = None,
    points: list[dict[str, int]] | None = None,
    theta: Any = None,
    sigma: Any = None,
    density: Any = None,
    frame_id: str = "frame-1",
    producer_build: str = "mm-1",
    observation: Mapping[str, Any] | None = None,
    supply_observation: bool = True,
) -> Any:
    held = _window(length=max(n, 1)) if window is None else window
    if points is None:
        if n == 1:
            points = [{"start": 0, "length": int(held["payload"]["window"]["length"])}]
        else:
            points = [{"start": index, "length": 1} for index in range(n)]
    arrays = _values(len(points))
    return build_measurement_artifact(
        held,
        axis,
        frame_id,
        points,
        arrays[0] if theta is None else theta,
        arrays[1] if sigma is None else sigma,
        arrays[2] if density is None else density,
        producer_build,
        _seal,
        None if axis is None or not supply_observation else observation or _observation(),
    )


def _validator() -> Any:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012

    blob = json.loads((_VENDOR / "common" / "blob.schema.json").read_text(encoding="utf-8"))
    schema = json.loads((_VENDOR / "meaning-measurement.schema.json").read_text(encoding="utf-8"))
    registry = Registry().with_resource(blob["$id"], Resource.from_contents(blob, DRAFT202012))
    return Draft202012Validator(schema, registry=registry)


def test_the_same_arguments_seal_the_same_envelope() -> None:
    for n, axis in ((1, None), (3, None), (1, _axis()), (3, _axis())):
        first = _build(n=n, axis=axis)
        second = _build(n=n, axis=axis)
        assert first.envelope == second.envelope
        assert first.blobs == second.blobs
        assert first.lookup == second.lookup
        assert list(_validator().iter_errors(first.envelope["payload"])) == []


def test_the_envelope_copies_the_window_and_follows_seq() -> None:
    window = _window(seq=2, space_id=None)
    axis = _axis(seq=5)
    artifact = _build(window=window, axis=axis)
    envelope = artifact.envelope
    assert envelope["kind"] == "interpretation"
    assert envelope["contract"] == {"id": "IC-00", "version": "1.1.0"}
    assert envelope["payload_schema"] == {"id": "nvs.meaning-measurement", "version": "0.1.0"}
    assert envelope["producer"] == {
        "name": "meaning-mapper",
        "version": __version__,
        "build": "mm-1",
    }
    assert envelope["session_id"] == window["session_id"]
    assert envelope["observation_id"] == window["observation_id"]
    assert envelope["space_id"] is None
    assert envelope["produced_at"] == window["produced_at"]
    assert envelope["seq"] == 6
    assert [item["role"] for item in envelope["parents"]] == ["source_window", "token_axis"]
    assert all(item["ordered"] is False for item in envelope["parents"])
    assert envelope["extensions"]["x-sensos-float-blob"].endswith("(S25)")
    assert set(artifact.stored_parents) == {_WINDOW, _AXIS, _OBS}
    assert artifact.stored_parents[_OBS]["envelope"]["payload"]["binding"]["alignment"] == (
        "decides-next/1"
    )
    assert artifact.lookup[_AXIS]["seq"] == 5
    only = _build(window=window)
    assert only.envelope["seq"] == 3
    assert only.envelope["payload"]["input"]["token_axis_artifact_id"] is None
    assert set(only.stored_parents) == {_WINDOW}


def test_a_small_asymmetry_that_is_spd_is_accepted() -> None:
    _theta, sigma, _density = _values(1)
    sigma[0, 0, 1] = 1e-9
    artifact = _build(sigma=sigma)
    assert artifact.envelope["payload"]["sigma"]["dtype"] == "float64"


def test_vendor_contract_bytes_match_the_lock() -> None:
    lock = json.loads((_VENDOR / "LOCK.json").read_text(encoding="utf-8"))
    files = lock["files"]
    present = sorted(
        path.relative_to(_VENDOR).as_posix()
        for path in _VENDOR.rglob("*")
        if path.is_file() and path.name not in {"LOCK.json", "README.md"}
    )
    assert present == sorted(files)
    for rel, entry in files.items():
        digest = hashlib.sha256((_VENDOR / rel).read_bytes()).hexdigest()
        assert digest == entry["vendored_sha256"], rel
        assert digest == entry["source_sha256"], rel


def test_vendor_contracts_match_sensos_when_the_directory_is_set() -> None:
    raw = os.environ.get("SENSOS_CONTRACTS_DIR")
    if not raw:
        pytest.skip("SENSOS_CONTRACTS_DIR is unset")
    root = Path(raw)
    lock = json.loads((_VENDOR / "LOCK.json").read_text(encoding="utf-8"))
    for rel, entry in lock["files"].items():
        source = entry["path"]
        if source.startswith(_CONTRACTS_PREFIX):
            source = source[len(_CONTRACTS_PREFIX) :]
        vendored = hashlib.sha256((_VENDOR / rel).read_bytes()).hexdigest()
        canonical = hashlib.sha256((root / source).read_bytes()).hexdigest()
        assert vendored == canonical, rel


def test_the_builder_does_not_import_sensos_or_the_runtimes() -> None:
    source = Path(build_measurement_artifact.__code__.co_filename).read_text(encoding="utf-8")
    banned = ("sensos", "msr", "nvs_runtime", "nvs")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        assert all(not name.startswith(banned) and name not in banned for name in names)


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ("frame", "frame_id"),
        ("build", "producer_build"),
        ("schema", "payload_schema"),
        ("producer", "producer"),
        ("artifact", "artifact_id"),
        ("space_missing", "space_id"),
        ("space_type", "space_id"),
        ("space_empty", "space_id"),
        ("seq", "seq"),
        ("seq_low", "seq"),
        ("length", "length"),
        ("points_type", "points"),
        ("points_empty", "points"),
        ("point_type", "points"),
        ("point_bool", "points"),
        ("point_length_type", "points"),
        ("point_negative", "points"),
        ("point_zero", "points"),
        ("point_past", "points"),
        ("point_huge", "points"),
        ("theta_type", "theta"),
        ("theta_rank", "theta"),
        ("theta_count", "theta"),
        ("theta_d", "theta"),
        ("sigma_shape", "sigma"),
        ("density_shape", "density"),
        ("theta_nan", "theta"),
        ("sigma_nan", "sigma"),
        ("density_inf", "density"),
        ("sigma_spd", "sigma"),
        ("density_low", "density"),
        ("density_high", "density"),
    ],
)
def test_a_bad_input_is_refused(change: str, field: str) -> None:
    kwargs = _refusal(change)
    with pytest.raises(MeasurementInputError) as caught:
        _build(**kwargs)
    assert caught.value.field == field


def _refusal(change: str) -> dict[str, Any]:
    window = _window()
    theta, sigma, density = _values(1)
    points: Any = [{"start": 0, "length": 4}]
    frame_id = "frame-1"
    producer_build = "mm-1"
    if change == "frame":
        frame_id = ""
    elif change == "build":
        producer_build = ""
    elif change == "schema":
        window["payload_schema"] = {"id": "msr.trajectory-window", "version": "0.9.0"}
    elif change == "producer":
        window["producer"] = {"name": "other"}
    elif change == "artifact":
        window["artifact_id"] = ""
    elif change == "space_missing":
        del window["space_id"]
    elif change == "space_type":
        window["space_id"] = 1
    elif change == "space_empty":
        window["space_id"] = ""
    elif change == "seq":
        window["seq"] = "2"
    elif change == "seq_low":
        window["seq"] = -1
    elif change == "length":
        window["payload"]["window"]["length"] = "4"
    elif change == "points_type":
        points = ({"start": 0, "length": 4},)
    elif change == "points_empty":
        points = []
    elif change == "point_type":
        points = ["row"]
    elif change == "point_bool":
        points = [{"start": True, "length": 1}]
    elif change == "point_length_type":
        points = [{"start": 0, "length": "1"}]
    elif change == "point_negative":
        points = [{"start": -1, "length": 1}]
    elif change == "point_zero":
        points = [{"start": 0, "length": 0}]
    elif change == "point_past":
        points = [{"start": 3, "length": 2}]
    elif change == "point_huge":
        points = [{"start": 2**53, "length": 1}]
    elif change == "theta_type":
        theta = {"no": 1}
    elif change == "theta_rank":
        theta = np.zeros(4)
    elif change == "theta_count":
        theta = np.zeros((2, _D))
    elif change == "theta_d":
        theta = np.zeros((1, 0))
    elif change == "sigma_shape":
        sigma = np.eye(3)
    elif change == "density_shape":
        density = np.zeros((1, 1))
    elif change == "theta_nan":
        theta = theta.copy()
        theta[0, 0] = np.nan
    elif change == "sigma_nan":
        sigma = sigma.copy()
        sigma[0, 0, 0] = np.inf
    elif change == "density_inf":
        density = np.array([np.inf])
    elif change == "sigma_spd":
        sigma = sigma.copy()
        sigma[0, 1, 1] = -1.0
    elif change == "density_low":
        density = np.array([-0.1])
    elif change == "density_high":
        density = np.array([1.1])
    return {
        "window": window,
        "points": points,
        "theta": theta,
        "sigma": sigma,
        "density": density,
        "frame_id": frame_id,
        "producer_build": producer_build,
    }


def test_an_axis_requires_the_observation() -> None:
    with pytest.raises(MeasurementInputError) as caught:
        _build(axis=_axis(), supply_observation=False)
    assert caught.value.field == "observation_envelope"
    refused = {
        "artifact_id": _observation(artifact_id="art:" + "9" * 64),
        "alignment": _observation(alignment="other"),
        "payload": _observation(alignment=None),
        "binding": _observation(binding=False),
    }
    fields = {
        "artifact_id": "artifact_id",
        "alignment": "alignment",
        "payload": "alignment",
        "binding": "alignment",
    }
    for name, observation in refused.items():
        with pytest.raises(MeasurementInputError) as caught:
            _build(axis=_axis(), observation=observation)
        assert caught.value.field == fields[name], name
    axis = _axis()
    axis["producer"] = "sensos-inference"
    with pytest.raises(MeasurementInputError) as caught:
        _build(axis=axis)
    assert caught.value.field == "producer"
    axis = _axis()
    axis["producer"]["name"] = "nvs-runtime"
    with pytest.raises(MeasurementInputError) as caught:
        _build(axis=axis)
    assert caught.value.field == "producer"


def test_a_token_temporal_that_does_not_match_is_refused() -> None:
    cases = {
        "payload_schema": _axis(schema=("nvs.token-temporal", "0.2.0")),
        "parents": _axis(parent="art:" + "9" * 64),
        "observation_id": _axis(observation_id="obs:" + "9" * 64),
        "n": _axis(n=3),
        "content_id": _axis(),
    }
    cases["content_id"]["content_id"] = ""
    broken = _axis()
    broken["payload"] = {"segments": [{"origin": "input", "n": 1}]}
    cases["generated"] = broken
    missing = _axis()
    missing["payload"] = {}
    cases["segments"] = missing
    negative = _axis()
    negative["payload"]["segments"][2]["n"] = -1
    cases["negative_n"] = negative
    text_n = _axis()
    text_n["payload"]["segments"][2]["n"] = "4"
    cases["text_n"] = text_n
    for field, axis in cases.items():
        expect = "n" if field in {"n", "generated", "segments", "negative_n", "text_n"} else field
        with pytest.raises(MeasurementInputError) as caught:
            _build(axis=axis)
        assert caught.value.field == expect, field


def test_jcs_rejects_values_outside_the_measurement_id() -> None:
    assert _jcs({"b": False, "a": True, "n": None, "s": 'x\n"\\', "i": [1]}) == (
        b'{"a":true,"b":false,"i":[1],"n":null,"s":"x\\n\\"\\\\"}'
    )
    assert _jcs("\u0001") == b'"\\u0001"'
    with pytest.raises(MeasurementInputError):
        _jcs(1.5)
    with pytest.raises(MeasurementInputError):
        _jcs(2**53)
    with pytest.raises(MeasurementInputError):
        _jcs({1: 2})
    with pytest.raises(MeasurementInputError):
        _jcs(object())
    with pytest.raises(MeasurementInputError):
        _jcs("\ud800")


def test_a_later_sigma_point_can_be_the_one_that_fails() -> None:
    _theta, sigma, _density = _values(2)
    sigma[1, 0, 0] = -1.0
    with pytest.raises(MeasurementInputError) as caught:
        _build(n=2, sigma=sigma)
    assert caught.value.field == "sigma"
    assert "point 1" in caught.value.detail


def test_length_above_the_safe_integer_is_refused() -> None:
    with pytest.raises(MeasurementInputError) as caught:
        _build(points=[{"start": 0, "length": 2**53}])
    assert caught.value.field == "points"


def test_a_missing_producer_object_is_refused() -> None:
    window = _window()
    window["producer"] = "nvs-runtime"
    with pytest.raises(MeasurementInputError) as caught:
        _build(window=window)
    assert caught.value.field == "producer"


def test_a_parent_that_is_not_one_id_is_refused() -> None:
    window = _window()
    axis = _axis()
    window["parents"] = []
    with pytest.raises(MeasurementInputError) as caught:
        _build(window=window, axis=axis)
    assert caught.value.field == "parents"
    window = _window()
    axis["parents"] = [{"role": "source_observation", "artifact_ids": []}]
    with pytest.raises(MeasurementInputError) as caught:
        _build(window=window, axis=axis)
    assert caught.value.field == "parents"
    axis["parents"] = [{"role": "source_observation", "artifact_ids": [1]}]
    with pytest.raises(MeasurementInputError) as caught:
        _build(window=window, axis=axis)
    assert caught.value.field == "parents"
    axis["parents"] = [1]
    with pytest.raises(MeasurementInputError) as caught:
        _build(window=window, axis=axis)
    assert caught.value.field == "parents"
    axis["parents"] = [{"artifact_ids": [""]}]
    with pytest.raises(MeasurementInputError) as caught:
        _build(window=window, axis=axis)
    assert caught.value.field == "parents"


def test_a_missing_nested_length_is_refused() -> None:
    window = _window()
    del window["payload"]["origin"]
    with pytest.raises(MeasurementInputError) as caught:
        _build(window=window, axis=_axis())
    assert caught.value.field == "length"
