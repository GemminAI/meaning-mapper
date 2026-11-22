"""The nvs.meaning-frame envelope is assembled from a WindowFrame."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from meaning_mapper.envelope import FrameInputError, build_frame_artifact
from meaning_mapper.window import WindowFrame

_VENDOR = Path(__file__).resolve().parent / "vendor_contracts"
_FIXED = "frame:sha256:a6beaa1ff6c1823a75319fb2d27027f6d6cded2e562875d87014a50b57004e2c"
_SPACE = "hid:" + "a" * 64
_SESSION = "ses:" + "b" * 64
_OBS = "obs:" + "c" * 64


def _seal(envelope: dict[str, Any], lookup: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(envelope)
    raw = json.dumps({"envelope": envelope, "lookup": lookup}, sort_keys=True).encode()
    digest = hashlib.sha256(raw).hexdigest()
    sealed["content_id"] = "cnt:" + digest
    sealed["artifact_id"] = "art:" + digest
    return sealed


def _observation(**overrides: Any) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "session_id": _SESSION,
        "observation_id": _OBS,
        "produced_at": "2026-11-21T00:00:00Z",
        "seq": 4,
        "space_id": _SPACE,
    }
    envelope.update(overrides)
    return envelope


def _fixed_frame() -> WindowFrame:
    mu = np.array([1.0, -0.0, 2.5], dtype=np.float64)
    basis = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 3.0]], dtype=np.float64)
    sigma0 = np.array([[2.0, 0.5], [0.5, 2.0]], dtype=np.float64)
    return WindowFrame(mu=mu, basis=basis, sigma0=sigma0)


def _build(
    frame: WindowFrame | None = None,
    source_space: str = _SPACE,
    observation: Mapping[str, Any] | None = None,
) -> Any:
    return build_frame_artifact(
        _fixed_frame() if frame is None else frame,
        source_space,
        "mm-test",
        _seal,
        _observation() if observation is None else observation,
    )


def _validator() -> Any:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012

    blob = json.loads((_VENDOR / "common" / "blob.schema.json").read_text(encoding="utf-8"))
    schema = json.loads((_VENDOR / "meaning-frame.schema.json").read_text(encoding="utf-8"))
    registry = Registry().with_resource(blob["$id"], Resource.from_contents(blob, DRAFT202012))
    return Draft202012Validator(schema, registry=registry)


def _recomputed(payload: Mapping[str, Any], blobs: Mapping[str, bytes]) -> str:
    chunks = [b"meaning-mapper.window-frame/1\n"]
    for name in ("mu", "basis", "sigma0"):
        shape = payload[name]["shape"]
        dims = " ".join(str(dim) for dim in shape)
        chunks.append(f"{name} {len(shape)} {dims}\n".encode("ascii"))
        chunks.append(blobs[payload[name]["uri"]])
    return "frame:sha256:" + hashlib.sha256(b"".join(chunks)).hexdigest()


def test_the_fixed_vector_keeps_the_sensos_frame_id() -> None:
    frame = _fixed_frame()
    assert frame.frame_id == _FIXED
    artifact = _build(frame)
    payload = artifact.envelope["payload"]
    assert payload["frame_id"] == _FIXED
    assert payload["frame_id"] == _recomputed(payload, artifact.blobs)
    assert list(_validator().iter_errors(payload)) == []
    assert artifact.envelope["parents"] == []
    assert artifact.envelope["space_id"] == _SPACE
    assert artifact.envelope["kind"] == "interpretation"
    assert artifact.envelope["producer"]["name"] == "meaning-mapper"


def test_a_source_space_of_the_wrong_form_is_refused() -> None:
    with pytest.raises(FrameInputError) as caught:
        _build(source_space="hid:" + "a" * 63)
    assert caught.value.field == "source_space"
    with pytest.raises(FrameInputError) as upper:
        _build(source_space="HID:" + "a" * 64)
    assert upper.value.field == "source_space"


def test_the_same_arguments_seal_the_same_content_id() -> None:
    first = _build()
    second = _build()
    assert first.envelope["content_id"] == second.envelope["content_id"]
    assert first.envelope == second.envelope
    assert first.blobs == second.blobs


def test_a_frame_that_is_not_a_window_frame_is_refused() -> None:
    with pytest.raises(FrameInputError) as caught:
        build_frame_artifact(None, _SPACE, "mm-test", _seal, _observation())
    assert caught.value.field == "frame"


def test_an_empty_or_non_string_producer_build_is_refused() -> None:
    frame = _fixed_frame()
    for producer_build in ("", None):
        with pytest.raises(FrameInputError) as caught:
            build_frame_artifact(frame, _SPACE, producer_build, _seal, _observation())
        assert caught.value.field == "producer_build"


def test_a_frame_id_that_differs_from_the_blob_bytes_is_refused() -> None:
    frame = _fixed_frame()
    object.__setattr__(frame, "frame_id", "frame:sha256:" + "0" * 64)
    with pytest.raises(FrameInputError) as caught:
        _build(frame)
    assert caught.value.field == "frame_id"


def test_an_observation_envelope_that_is_not_a_mapping_is_refused() -> None:
    with pytest.raises(FrameInputError) as caught:
        build_frame_artifact(_fixed_frame(), _SPACE, "mm-test", _seal, ["not-a-mapping"])
    assert caught.value.field == "observation_envelope"


def test_a_session_id_of_the_wrong_form_is_refused() -> None:
    with pytest.raises(FrameInputError) as caught:
        _build(observation=_observation(session_id="ses:" + "b" * 63))
    assert caught.value.field == "session_id"
    with pytest.raises(FrameInputError) as caught:
        _build(observation=_observation(session_id=None))
    assert caught.value.field == "session_id"


def test_an_observation_id_that_is_neither_null_nor_an_obs_id_is_refused() -> None:
    with pytest.raises(FrameInputError) as caught:
        _build(observation=_observation(observation_id="obs:" + "c" * 63))
    assert caught.value.field == "observation_id"
    with pytest.raises(FrameInputError) as caught:
        _build(observation=_observation(observation_id=1))
    assert caught.value.field == "observation_id"


def test_a_missing_or_empty_produced_at_is_refused() -> None:
    missing = _observation()
    del missing["produced_at"]
    with pytest.raises(FrameInputError) as caught:
        _build(observation=missing)
    assert caught.value.field == "produced_at"
    with pytest.raises(FrameInputError) as caught:
        _build(observation=_observation(produced_at=""))
    assert caught.value.field == "produced_at"


def test_a_seq_outside_the_accepted_integers_is_refused() -> None:
    for seq in ("4", -1, 2**53 - 1):
        with pytest.raises(FrameInputError) as caught:
            _build(observation=_observation(seq=seq))
        assert caught.value.field == "seq"
