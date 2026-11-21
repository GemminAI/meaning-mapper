"""Measure window rows in a frame the caller supplies.

The frame is an input. This module does not store it, and it does not change
the HEXT observation pipeline. A point covering rows ``[start, start + n)`` is

- ``x̄ = mean(rows)`` in float64
- ``theta = B (x̄ − μ)``
- ``sigma = Σ0 / n``
- ``density = compute_semantic_density(theta)``

``sigma`` does not include the spread of the rows inside the point.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from meaning_mapper._linalg import is_spd
from meaning_mapper.density.density_estimation import compute_semantic_density

FloatArray = NDArray[np.float64]
_DOMAIN = "meaning-mapper.window-frame/1"


class WindowMeasureError(Exception):
    """A required value is missing or does not match. Nothing is filled in."""

    def __init__(self, field: str, detail: str) -> None:
        super().__init__(f"{field}: {detail}")
        self.field = field
        self.detail = detail


@dataclass(frozen=True, slots=True)
class WindowFrame:
    """``(frame_id, μ, B, Σ0)``. ``d`` is the number of rows of ``B``.

    Omit ``frame_id`` to use :func:`frame_content_id`. A supplied id is kept
    even when it differs from the content id: it is a name, not a check.
    """

    mu: FloatArray
    basis: FloatArray
    sigma0: FloatArray
    frame_id: str | None = None

    def __post_init__(self) -> None:
        mu = _floats("mu", self.mu, 1)
        basis = _floats("basis", self.basis, 2)
        sigma0 = _floats("sigma0", self.sigma0, 2)
        if basis.shape[1] != mu.shape[0]:
            raise WindowMeasureError("basis", f"D {basis.shape[1]} != mu length {mu.shape[0]}")
        if sigma0.shape != (basis.shape[0], basis.shape[0]):
            raise WindowMeasureError(
                "sigma0",
                f"shape {tuple(int(dim) for dim in sigma0.shape)} != {(basis.shape[0],) * 2}",
            )
        if not is_spd(sigma0):
            raise WindowMeasureError("sigma0", "not symmetric positive definite")
        object.__setattr__(self, "mu", mu)
        object.__setattr__(self, "basis", basis)
        object.__setattr__(self, "sigma0", sigma0)
        if self.frame_id is None:
            object.__setattr__(self, "frame_id", frame_content_id(mu, basis, sigma0))
        elif not isinstance(self.frame_id, str) or not self.frame_id:
            raise WindowMeasureError("frame_id", "omit it, or pass a non-empty string")


@dataclass(frozen=True, slots=True)
class WindowMeasurement:
    """``theta`` is ``N × d``, ``sigma`` is ``N × d × d``, ``density`` is ``N``."""

    theta: FloatArray
    sigma: FloatArray
    density: FloatArray


def frame_content_id(mu: Any, basis: Any, sigma0: Any) -> str:
    """SHA-256 hex of the frame bytes. Usable as ``frame_id``.

    The hashed bytes are the domain ``meaning-mapper.window-frame/1``, then
    each array's name, rank, and shape, then that array as little-endian
    C-order float64. See ``docs/WINDOW_MEASUREMENT.md``.
    """
    return hashlib.sha256(_content_bytes(mu, basis, sigma0)).hexdigest()


def window_rows(window_envelope: Mapping[str, Any], blobs: Mapping[str, bytes]) -> FloatArray:
    """The window's ``points`` blob as a float64 matrix ``[length, dimension]``.

    The blob is float32, little-endian, C order. The uri's sha256 and the
    byte count are checked. A mismatch raises :class:`WindowMeasureError`.
    """
    payload = window_envelope.get("payload")
    if not isinstance(payload, Mapping):
        raise WindowMeasureError("payload", "the window has no payload")
    length = _path_int(payload, ("window", "length"))
    dimension = _path_int(payload, ("dimension",))
    if length < 1 or dimension < 1:
        raise WindowMeasureError("shape", f"length {length}, dimension {dimension}")
    points = payload.get("points")
    if not isinstance(points, Mapping):
        raise WindowMeasureError("points", "the window has no points blob")
    if points.get("dtype") != "float32":
        raise WindowMeasureError("points", "dtype is not float32")
    if points.get("byte_order") != "little":
        raise WindowMeasureError("points", "byte_order is not little")
    if points.get("order") != "C":
        raise WindowMeasureError("points", "order is not C")
    if points.get("shape") != [length, dimension]:
        raise WindowMeasureError(
            "shape", f"points.shape {points.get('shape')!r} != [{length}, {dimension}]"
        )
    digest = points.get("sha256")
    uri = points.get("uri")
    if not isinstance(digest, str) or uri != "blob:sha256:" + digest:
        raise WindowMeasureError("sha256", "the points uri is not its sha256")
    if not isinstance(blobs, Mapping):
        raise WindowMeasureError("points", "blobs is not a mapping")
    raw = blobs.get(uri)
    if not isinstance(raw, (bytes, bytearray)):
        raise WindowMeasureError("points", "the points blob is not in blobs")
    expected = length * dimension * 4
    if len(raw) != expected:
        raise WindowMeasureError("points", f"{len(raw)} bytes, expected {expected}")
    if hashlib.sha256(raw).hexdigest() != digest:
        raise WindowMeasureError("sha256", "sha256 of the points bytes is not the uri")
    values = np.frombuffer(bytes(raw), dtype="<f4").reshape(length, dimension)
    return np.array(values, dtype=np.float64, copy=True, order="C")


def measure_window(
    rows: Any, points: Sequence[Mapping[str, Any]], frame: WindowFrame
) -> WindowMeasurement:
    """``points`` is a list of ``{start, length}`` ranges on ``rows``.

    A range past the row count, a frame whose ``D`` is not the row width, or a
    non-finite value raises :class:`WindowMeasureError`. Nothing is filled in.
    """
    held = _floats("rows", rows, 2)
    if frame.basis.shape[1] != held.shape[1]:
        raise WindowMeasureError(
            "dimension", f"frame D {frame.basis.shape[1]} != row width {held.shape[1]}"
        )
    parsed = _points(points, int(held.shape[0]))
    count = len(parsed)
    width = int(frame.basis.shape[0])
    theta = np.empty((count, width), dtype=np.float64)
    sigma = np.empty((count, width, width), dtype=np.float64)
    density = np.empty(count, dtype=np.float64)
    for index, (start, length) in enumerate(parsed):
        mean = np.mean(held[start : start + length], axis=0, dtype=np.float64)
        theta[index] = frame.basis @ (mean - frame.mu)
        sigma[index] = frame.sigma0 / length
        density[index] = compute_semantic_density(theta[index])
    if not bool(np.isfinite(theta).all()):
        raise WindowMeasureError("theta", "a NaN or an infinity")
    return WindowMeasurement(theta=theta, sigma=sigma, density=density)


def _content_bytes(mu: Any, basis: Any, sigma0: Any) -> bytes:
    chunks = [f"{_DOMAIN}\n".encode("ascii")]
    for name, value in (("mu", mu), ("basis", basis), ("sigma0", sigma0)):
        array = _content_array(name, value)
        dims = " ".join(str(int(dim)) for dim in array.shape)
        chunks.append(f"{name} {array.ndim} {dims}\n".encode("ascii"))
        chunks.append(array.tobytes())
    return b"".join(chunks)


def _content_array(field: str, value: Any) -> FloatArray:
    try:
        array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise WindowMeasureError(field, f"not a float64 array: {error}") from error
    return np.array(array, dtype=np.float64, copy=True, order="C")


def _floats(field: str, value: Any, ndim: int) -> FloatArray:
    array = _content_array(field, value)
    if array.ndim != ndim:
        raise WindowMeasureError(field, f"ndim {array.ndim} != {ndim}")
    if any(dim < 1 for dim in array.shape):
        raise WindowMeasureError(field, f"shape {tuple(int(dim) for dim in array.shape)} is empty")
    if not bool(np.isfinite(array).all()):
        raise WindowMeasureError(field, "a NaN or an infinity")
    array.setflags(write=False)
    return array


def _path_int(payload: Mapping[str, Any], path: tuple[str, ...]) -> int:
    current: Any = payload
    for part in path:
        if not isinstance(current, Mapping) or part not in current:
            raise WindowMeasureError(path[-1], "not on the window payload")
        current = current[part]
    if type(current) is not int or current < 0:
        raise WindowMeasureError(path[-1], f"{current!r} is not an integer >= 0")
    return current


def _points(points: Sequence[Mapping[str, Any]], n_rows: int) -> list[tuple[int, int]]:
    if not isinstance(points, list) or not points:
        raise WindowMeasureError("points", "at least one point is required")
    parsed: list[tuple[int, int]] = []
    for index, point in enumerate(points):
        if not isinstance(point, Mapping):
            raise WindowMeasureError("points", f"point {index} is not an object")
        start = point.get("start")
        length = point.get("length")
        if type(start) is not int or type(length) is not int or start < 0 or length < 1:
            raise WindowMeasureError("points", f"point {index} needs start >= 0 and length >= 1")
        if start + length > n_rows:
            raise WindowMeasureError("points", f"point {index} rows pass the window length")
        parsed.append((start, length))
    return parsed
