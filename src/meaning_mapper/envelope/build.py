"""Assemble one ``nvs.meaning-measurement`` 0.1.0 envelope.

The caller passes ``theta``, ``sigma``, and ``density``. This module does not
project a window onto a measurement, and it does not import sensos: ``seal``
is the caller's ``seal(envelope, lookup)``.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from meaning_mapper._linalg import is_spd
from meaning_mapper.version import __version__

IC00_ID = "IC-00"
IC00_VERSION = "1.1.0"
PAYLOAD_SCHEMA = {"id": "nvs.meaning-measurement", "version": "0.1.0"}
WINDOW_SCHEMA = ("msr.trajectory-window", "0.10.0")
AXIS_SCHEMA = ("nvs.token-temporal", "0.1.0")
AXIS_PRODUCER = "sensos-inference"
WINDOW_PRODUCER = "nvs-runtime"
ALIGNMENT = "decides-next/1"
PRODUCER_NAME = "meaning-mapper"
ID_DOMAIN = "nvs.meaning-measurement/1"
MEDIA_TYPE = "application/vnd.sensos.ndarray-raw"
FLOAT_BLOB_REASON = (
    "theta, sigma, and density are float64 blobs so the values stay bit-reproducible (S25)"
)
_PLACEHOLDER_CONTENT = "cnt:" + "0" * 64
_PLACEHOLDER_ARTIFACT = "art:" + "0" * 64
_MAX_SAFE = 2**53 - 1
_FRAME_ID = re.compile(r"^frame:sha256:[0-9a-f]{64}$")
_SHORT = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f", "\n": "\\n", "\r": "\\r", "\t": "\\t"}

FloatArray = NDArray[np.float64]
Seal = Callable[[dict[str, Any], dict[str, Any]], Mapping[str, Any]]


class MeasurementInputError(Exception):
    """A required value is missing or does not match. Nothing is filled in."""

    def __init__(self, field: str, detail: str) -> None:
        super().__init__(f"{field}: {detail}")
        self.field = field
        self.detail = detail


@dataclass(frozen=True, slots=True)
class MeasurementArtifact:
    """The sealed envelope and the bytes the Gate needs beside it."""

    envelope: dict[str, Any]
    stored_parents: dict[str, Any]
    blobs: dict[str, bytes]
    lookup: dict[str, Any]


def build_measurement_artifact(
    window_envelope: Mapping[str, Any],
    token_temporal_envelope: Mapping[str, Any] | None,
    frame_id: str,
    points: Sequence[Mapping[str, Any]],
    theta: Any,
    sigma: Any,
    density: Any,
    producer_build: str,
    seal: Seal,
    observation_envelope: Mapping[str, Any] | None = None,
) -> MeasurementArtifact:
    """Seal a measurement of ``points`` on ``window_envelope``.

    ``token_temporal_envelope`` may be omitted. When it is given,
    ``observation_envelope`` is required. The same arguments produce the same
    envelope: nothing here reads a clock or a random source.
    """
    if not isinstance(frame_id, str) or _FRAME_ID.fullmatch(frame_id) is None:
        raise MeasurementInputError("frame_id", "must be frame:sha256: and 64 lowercase hex digits")
    if not isinstance(producer_build, str) or not producer_build:
        raise MeasurementInputError("producer_build", "must be a non-empty string")
    _require_window(window_envelope)
    parsed = _points(points, _nested_int(window_envelope, ("payload", "window", "length")))
    if token_temporal_envelope is not None:
        _require_axis(window_envelope, token_temporal_envelope, observation_envelope)
    count = len(parsed)
    theta_array = _floats("theta", theta)
    if theta_array.ndim != 2 or theta_array.shape[0] != count or int(theta_array.shape[1]) < 1:
        shape = tuple(int(dim) for dim in theta_array.shape)
        raise MeasurementInputError("theta", f"shape {shape} is not [N,d]")
    dimension = int(theta_array.shape[1])
    sigma_array = _floats("sigma", sigma)
    _shape("sigma", sigma_array, (count, dimension, dimension))
    density_array = _floats("density", density)
    _shape("density", density_array, (count,))
    _finite(theta_array, sigma_array, density_array)
    _sigma(sigma_array)
    _density(density_array)
    payload, blobs = _payload(
        frame_id,
        window_envelope,
        token_temporal_envelope,
        parsed,
        theta_array,
        sigma_array,
        density_array,
    )
    lookup = _lookup(window_envelope, token_temporal_envelope)
    envelope = _envelope(window_envelope, token_temporal_envelope, payload, producer_build, lookup)
    sealed = dict(seal(dict(envelope), lookup))
    return MeasurementArtifact(
        envelope=sealed,
        stored_parents=_stored(window_envelope, token_temporal_envelope, observation_envelope),
        blobs=blobs,
        lookup=lookup,
    )


def _require_window(envelope: Mapping[str, Any]) -> None:
    _schema(envelope, WINDOW_SCHEMA, "the window is not msr.trajectory-window 0.10.0")
    producer = envelope.get("producer")
    name = producer.get("name") if isinstance(producer, Mapping) else None
    if name != WINDOW_PRODUCER:
        raise MeasurementInputError("producer", "the window producer is not nvs-runtime")
    for key in ("artifact_id", "content_id", "session_id", "observation_id", "produced_at"):
        _text(envelope, key)
    _seq(envelope)
    if "space_id" not in envelope:
        raise MeasurementInputError("space_id", "not on the window envelope")
    space_id = envelope["space_id"]
    if space_id is not None and not isinstance(space_id, str):
        raise MeasurementInputError("space_id", "must be null or a string")
    if isinstance(space_id, str) and not space_id:
        raise MeasurementInputError("space_id", "must be null or a non-empty string")


def _require_axis(
    window: Mapping[str, Any],
    axis: Mapping[str, Any],
    observation: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    _schema(axis, AXIS_SCHEMA, "the token temporal is not nvs.token-temporal 0.1.0")
    producer = axis.get("producer")
    name = producer.get("name") if isinstance(producer, Mapping) else None
    if name != AXIS_PRODUCER:
        raise MeasurementInputError(
            "producer", "the token temporal producer is not sensos-inference"
        )
    for key in ("artifact_id", "content_id"):
        _text(axis, key)
    _seq(axis)
    if _parent_id(window) != _parent_id(axis):
        raise MeasurementInputError(
            "parents", "the window and the token temporal do not share an observation"
        )
    if _text(axis, "observation_id") != _text(window, "observation_id"):
        raise MeasurementInputError("observation_id", "differs from the window")
    origin = _nested_int(window, ("payload", "origin", "length"))
    if origin != _generated_n(axis):
        raise MeasurementInputError("n", "origin.length differs from generated n")
    if observation is None:
        raise MeasurementInputError("observation_envelope", "required when a token axis is given")
    if _parent_id(window) != _text(observation, "artifact_id"):
        raise MeasurementInputError("artifact_id", "the parents are not this observation")
    _alignment(observation)
    return observation


def _alignment(observation: Mapping[str, Any]) -> None:
    payload = observation.get("payload")
    binding = payload.get("binding") if isinstance(payload, Mapping) else None
    alignment = binding.get("alignment") if isinstance(binding, Mapping) else None
    if alignment != ALIGNMENT:
        raise MeasurementInputError("alignment", f"{alignment!r} is not decides-next/1")


def _schema(envelope: Mapping[str, Any], expected: tuple[str, str], detail: str) -> None:
    schema = envelope.get("payload_schema")
    ident = (schema.get("id"), schema.get("version")) if isinstance(schema, Mapping) else None
    if ident != expected:
        raise MeasurementInputError("payload_schema", detail)


def _text(envelope: Mapping[str, Any], key: str) -> str:
    value = envelope.get(key)
    if not isinstance(value, str) or not value:
        raise MeasurementInputError(key, "not on the envelope")
    return value


def _seq(envelope: Mapping[str, Any]) -> int:
    seq = envelope.get("seq")
    if type(seq) is not int or seq < 0:
        raise MeasurementInputError("seq", f"{seq!r} is not an integer >= 0")
    return seq


def _parent_id(envelope: Mapping[str, Any]) -> str:
    parents = envelope.get("parents")
    entry = parents[0] if isinstance(parents, list) and len(parents) == 1 else None
    ids = entry.get("artifact_ids") if isinstance(entry, Mapping) else None
    if not isinstance(ids, list) or len(ids) != 1 or not isinstance(ids[0], str) or not ids[0]:
        raise MeasurementInputError("parents", "needs exactly one parent artifact_id")
    return ids[0]


def _nested_int(envelope: Mapping[str, Any], path: tuple[str, ...]) -> int:
    current: Any = envelope
    for part in path:
        if not isinstance(current, Mapping) or part not in current:
            raise MeasurementInputError(path[-1], "not in the envelope")
        current = current[part]
    if type(current) is not int or current < 0:
        raise MeasurementInputError(path[-1], f"{current!r} is not an integer >= 0")
    return current


def _generated_n(axis: Mapping[str, Any]) -> int:
    payload = axis.get("payload")
    segments = payload.get("segments") if isinstance(payload, Mapping) else None
    found: list[Any] = []
    if isinstance(segments, list):
        found = [
            item.get("n")
            for item in segments
            if isinstance(item, Mapping) and item.get("origin") == "generated"
        ]
    if len(found) != 1 or type(found[0]) is not int or found[0] < 0:
        raise MeasurementInputError("n", "generated n is not on the token temporal payload")
    n: int = found[0]
    return n


def _points(points: Sequence[Mapping[str, Any]], window_length: int) -> list[tuple[int, int]]:
    if not isinstance(points, list) or not points:
        raise MeasurementInputError("points", "at least one point is required")
    parsed: list[tuple[int, int]] = []
    for index, point in enumerate(points):
        if not isinstance(point, Mapping):
            raise MeasurementInputError("points", f"point {index} is not an object")
        start = point.get("start")
        length = point.get("length")
        if type(start) is not int or type(length) is not int or start < 0 or length < 1:
            raise MeasurementInputError("points", f"point {index} needs start >= 0 and length >= 1")
        if start > _MAX_SAFE or length > _MAX_SAFE or start + length > window_length:
            raise MeasurementInputError("points", f"point {index} rows pass the window length")
        parsed.append((start, length))
    return parsed


def _floats(field: str, value: Any) -> FloatArray:
    try:
        array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise MeasurementInputError(field, f"not a float64 array: {error}") from error
    return np.ascontiguousarray(array)


def _shape(field: str, array: FloatArray, expected: tuple[int, ...]) -> None:
    if array.shape != expected:
        got = tuple(int(dim) for dim in array.shape)
        raise MeasurementInputError(field, f"shape {got} != {expected}")


def _finite(theta: FloatArray, sigma: FloatArray, density: FloatArray) -> None:
    for field, array in (("theta", theta), ("sigma", sigma), ("density", density)):
        if not bool(np.isfinite(array).all()):
            raise MeasurementInputError(field, "a NaN or an infinity")


def _sigma(sigma: FloatArray) -> None:
    for index in range(int(sigma.shape[0])):
        if not is_spd(sigma[index]):
            raise MeasurementInputError(
                "sigma", f"point {index} is not symmetric positive definite"
            )


def _density(density: FloatArray) -> None:
    if bool(np.any((density < 0.0) | (density > 1.0))):
        raise MeasurementInputError("density", "a value is outside [0, 1]")


def _payload(
    frame_id: str,
    window: Mapping[str, Any],
    axis: Mapping[str, Any] | None,
    points: list[tuple[int, int]],
    theta: FloatArray,
    sigma: FloatArray,
    density: FloatArray,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    theta_ref, theta_bytes = _blob(theta)
    sigma_ref, sigma_bytes = _blob(sigma)
    density_ref, density_bytes = _blob(density)
    payload: dict[str, Any] = {
        "measurement_id": "0" * 64,
        "frame_id": frame_id,
        "input": {
            "kind": "window",
            "window_artifact_id": window["artifact_id"],
            "token_axis_artifact_id": None if axis is None else axis["artifact_id"],
        },
        "points": [{"rows": {"start": start, "length": length}} for start, length in points],
        "theta": theta_ref,
        "sigma": sigma_ref,
        "density": density_ref,
    }
    payload["measurement_id"] = hashlib.sha256(_jcs(_id_body(payload))).hexdigest()
    blobs = {
        theta_ref["uri"]: theta_bytes,
        sigma_ref["uri"]: sigma_bytes,
        density_ref["uri"]: density_bytes,
    }
    return payload, blobs


def _id_body(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "domain": ID_DOMAIN,
        "frame_id": payload["frame_id"],
        "input": payload["input"],
        "points": payload["points"],
        "theta.sha256": payload["theta"]["sha256"],
        "sigma.sha256": payload["sigma"]["sha256"],
        "density.sha256": payload["density"]["sha256"],
    }


def _blob(array: FloatArray) -> tuple[dict[str, Any], bytes]:
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


def _lookup(
    window: Mapping[str, Any],
    axis: Mapping[str, Any] | None,
) -> dict[str, Any]:
    lookup = {_text(window, "artifact_id"): _ref(window)}
    if axis is not None:
        lookup[_text(axis, "artifact_id")] = _ref(axis)
    return lookup


def _ref(envelope: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "content_id": _text(envelope, "content_id"),
        "seq": _seq(envelope),
        "observation_id": _text(envelope, "observation_id"),
    }


def _stored(
    window: Mapping[str, Any],
    axis: Mapping[str, Any] | None,
    observation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    stored = {window["artifact_id"]: {"envelope": window}}
    if axis is not None:
        observed = cast(Mapping[str, Any], observation)
        stored[axis["artifact_id"]] = {"envelope": axis}
        stored[observed["artifact_id"]] = {"envelope": observed}
    return stored


def _envelope(
    window: Mapping[str, Any],
    axis: Mapping[str, Any] | None,
    payload: dict[str, Any],
    producer_build: str,
    lookup: Mapping[str, Any],
) -> dict[str, Any]:
    parents = [
        {"role": "source_window", "ordered": False, "artifact_ids": [window["artifact_id"]]},
    ]
    if axis is not None:
        parents.append(
            {"role": "token_axis", "ordered": False, "artifact_ids": [axis["artifact_id"]]}
        )
    seqs = [item["seq"] for item in lookup.values()]
    return {
        "contract": {"id": IC00_ID, "version": IC00_VERSION},
        "content_id": _PLACEHOLDER_CONTENT,
        "artifact_id": _PLACEHOLDER_ARTIFACT,
        "kind": "interpretation",
        "payload_schema": dict(PAYLOAD_SCHEMA),
        "payload": payload,
        "producer": {"name": PRODUCER_NAME, "version": __version__, "build": producer_build},
        "session_id": window["session_id"],
        "observation_id": window["observation_id"],
        "event_span": None,
        "space_id": window["space_id"],
        "parents": parents,
        "policy_refs": [],
        "calibration_ref": None,
        "rule_refs": [],
        "observed_at": None,
        "seq": max(seqs) + 1,
        "produced_at": window["produced_at"],
        "extensions": {"x-sensos-float-blob": FLOAT_BLOB_REASON},
    }


def _jcs(value: Any) -> bytes:
    """RFC 8785 bytes for the measurement id. Integers only, same rules as the Gate."""
    return _canon(value).encode("utf-8")


def _canon(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float):
        raise MeasurementInputError("jcs", f"float {value!r} is not allowed")
    if isinstance(value, int):
        if abs(value) > _MAX_SAFE:
            raise MeasurementInputError("jcs", f"{value} outside +-(2^53-1)")
        return str(value)
    if isinstance(value, str):
        return _string(value)
    if isinstance(value, list):
        return "[" + ",".join(_canon(item) for item in value) + "]"
    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                raise MeasurementInputError("jcs", f"object key {key!r} is not a string")
        keys = sorted(value, key=lambda key: key.encode("utf-16-be", "surrogatepass"))
        return "{" + ",".join(_string(key) + ":" + _canon(value[key]) for key in keys) + "}"
    raise MeasurementInputError("jcs", f"{type(value).__name__} cannot be canonicalized")


def _string(text: str) -> str:
    out = ['"']
    for char in text:
        code = ord(char)
        if 0xD800 <= code <= 0xDFFF:
            raise MeasurementInputError("jcs", "lone surrogate in a string")
        if char in _SHORT:
            out.append(_SHORT[char])
        elif code < 0x20:
            out.append(f"\\u{code:04x}")
        else:
            out.append(char)
    out.append('"')
    return "".join(out)
