"""Assemble one ``nvs.meaning-frame`` 0.1.0 envelope.

The caller passes a :class:`~meaning_mapper.window.WindowFrame`. This module
does not choose the frame, and it does not import sensos: ``seal`` is the
caller's ``seal(envelope, lookup)``.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from meaning_mapper.version import __version__
from meaning_mapper.window.measure import WindowFrame

IC00_ID = "IC-00"
IC00_VERSION = "1.1.0"
PAYLOAD_SCHEMA = {"id": "nvs.meaning-frame", "version": "0.1.0"}
PRODUCER_NAME = "meaning-mapper"
CONTENT_RULE = "meaning-mapper.window-frame/1"
MEDIA_TYPE = "application/vnd.sensos.ndarray-raw"
FLOAT_BLOB_REASON = (
    "mu, basis, and sigma0 are float64 blobs so the values stay bit-reproducible (S25)"
)
_PLACEHOLDER_CONTENT = "cnt:" + "0" * 64
_PLACEHOLDER_ARTIFACT = "art:" + "0" * 64
_MAX_SAFE = 2**53 - 1
_HID = re.compile(r"^hid:[0-9a-f]{64}$")
_SESSION = re.compile(r"^ses:[0-9a-f]{64}$")
_OBSERVATION = re.compile(r"^obs:[0-9a-f]{64}$")
_ARRAYS = ("mu", "basis", "sigma0")

Seal = Callable[[dict[str, Any], dict[str, Any]], Mapping[str, Any]]


class FrameInputError(Exception):
    """A required value is missing or does not match. Nothing is filled in."""

    def __init__(self, field: str, detail: str) -> None:
        super().__init__(f"{field}: {detail}")
        self.field = field
        self.detail = detail


@dataclass(frozen=True, slots=True)
class FrameArtifact:
    """The sealed envelope and the bytes the Gate needs beside it."""

    envelope: dict[str, Any]
    stored_parents: dict[str, Any]
    blobs: dict[str, bytes]
    lookup: dict[str, Any]


def build_frame_artifact(
    frame: WindowFrame,
    source_space: str,
    producer_build: str,
    seal: Seal,
    observation_envelope: Mapping[str, Any],
) -> FrameArtifact:
    """Seal ``frame`` as ``nvs.meaning-frame`` 0.1.0.

    The same arguments produce the same envelope: nothing here reads a clock
    or a random source. ``frame_id`` is checked again from the blob bytes.
    """
    if not isinstance(frame, WindowFrame):
        raise FrameInputError("frame", "must be a WindowFrame")
    if not isinstance(source_space, str) or _HID.fullmatch(source_space) is None:
        raise FrameInputError("source_space", "must be hid: and 64 lowercase hex digits")
    if not isinstance(producer_build, str) or not producer_build:
        raise FrameInputError("producer_build", "must be a non-empty string")
    session_id, observation_id, produced_at, seq = _observation(observation_envelope)
    payload, blobs = _payload(frame, source_space)
    recomputed = _frame_id(payload, blobs)
    if recomputed != frame.frame_id:
        raise FrameInputError("frame_id", "differs from the blob bytes")
    lookup: dict[str, Any] = {}
    envelope = _envelope(
        payload, producer_build, session_id, observation_id, produced_at, seq, source_space
    )
    sealed = dict(seal(dict(envelope), lookup))
    return FrameArtifact(envelope=sealed, stored_parents={}, blobs=blobs, lookup=lookup)


def _observation(envelope: Mapping[str, Any]) -> tuple[str, str | None, str, int]:
    if not isinstance(envelope, Mapping):
        raise FrameInputError("observation_envelope", "must be a mapping")
    session_id = envelope.get("session_id")
    if not isinstance(session_id, str) or _SESSION.fullmatch(session_id) is None:
        raise FrameInputError("session_id", "must be ses: and 64 lowercase hex digits")
    observation_id = envelope.get("observation_id")
    if observation_id is not None and (
        not isinstance(observation_id, str) or _OBSERVATION.fullmatch(observation_id) is None
    ):
        raise FrameInputError("observation_id", "must be null or obs: and 64 lowercase hex digits")
    produced_at = envelope.get("produced_at")
    if not isinstance(produced_at, str) or not produced_at:
        raise FrameInputError("produced_at", "not on the observation envelope")
    seq = envelope.get("seq")
    if type(seq) is not int or seq < 0 or seq >= _MAX_SAFE:
        raise FrameInputError("seq", f"{seq!r} is not an integer >= 0")
    return session_id, observation_id, produced_at, seq


def _payload(frame: WindowFrame, source_space: str) -> tuple[dict[str, Any], dict[str, bytes]]:
    arrays = {"mu": frame.mu, "basis": frame.basis, "sigma0": frame.sigma0}
    refs: dict[str, dict[str, Any]] = {}
    blobs: dict[str, bytes] = {}
    for name in _ARRAYS:
        ref, raw = _blob(arrays[name])
        refs[name] = ref
        blobs[ref["uri"]] = raw
    payload = {
        "frame_id": frame.frame_id,
        "content_rule": CONTENT_RULE,
        "d": int(frame.basis.shape[0]),
        "D": int(frame.mu.shape[0]),
        "source_space": source_space,
        "mu": refs["mu"],
        "basis": refs["basis"],
        "sigma0": refs["sigma0"],
    }
    return payload, blobs


def _blob(array: Any) -> tuple[dict[str, Any], bytes]:
    raw = np.ascontiguousarray(array, dtype="<f8").tobytes()
    digest = hashlib.sha256(raw).hexdigest()
    ref = {
        "uri": "blob:sha256:" + digest,
        "sha256": digest,
        "media_type": MEDIA_TYPE,
        "dtype": "float64",
        "shape": [int(dim) for dim in array.shape],
        "byte_order": "little",
        "order": "C",
        "comparison": {"rule": "absolute_error", "bound": {"base": 2, "exponent": -40}},
        "unit": "1",
    }
    return ref, raw


def _frame_id(payload: Mapping[str, Any], blobs: Mapping[str, bytes]) -> str:
    chunks = [f"{CONTENT_RULE}\n".encode("ascii")]
    for name in _ARRAYS:
        shape = payload[name]["shape"]
        dims = " ".join(str(dim) for dim in shape)
        chunks.append(f"{name} {len(shape)} {dims}\n".encode("ascii"))
        chunks.append(blobs[payload[name]["uri"]])
    return "frame:sha256:" + hashlib.sha256(b"".join(chunks)).hexdigest()


def _envelope(
    payload: dict[str, Any],
    producer_build: str,
    session_id: str,
    observation_id: str | None,
    produced_at: str,
    seq: int,
    source_space: str,
) -> dict[str, Any]:
    return {
        "contract": {"id": IC00_ID, "version": IC00_VERSION},
        "content_id": _PLACEHOLDER_CONTENT,
        "artifact_id": _PLACEHOLDER_ARTIFACT,
        "kind": "interpretation",
        "payload_schema": dict(PAYLOAD_SCHEMA),
        "payload": payload,
        "producer": {"name": PRODUCER_NAME, "version": __version__, "build": producer_build},
        "session_id": session_id,
        "observation_id": observation_id,
        "event_span": None,
        "space_id": source_space,
        "parents": [],
        "policy_refs": [],
        "calibration_ref": None,
        "rule_refs": [],
        "observed_at": None,
        "seq": seq + 1,
        "produced_at": produced_at,
        "extensions": {"x-sensos-float-blob": FLOAT_BLOB_REASON},
    }
