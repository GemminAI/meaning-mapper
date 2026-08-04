"""Private SPD-matrix helpers shared by the metric/frame/covariance stages.

Not part of the public API. Every function here is pure and deterministic:
same input array, same output, every time.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
Vector = tuple[float, ...]
Matrix = tuple[tuple[float, ...], ...]


def symmetrize(matrix: FloatArray) -> FloatArray:
    """Average a matrix with its transpose to remove float asymmetry."""
    return (matrix + matrix.T) * 0.5


def clamp_eigenvalues(matrix: FloatArray, floor: float, ceiling: float) -> FloatArray:
    """Clamp a symmetric matrix's eigenvalues into ``[floor, ceiling]``.

    Rebuilds the matrix from the clamped spectrum, so the result is always
    symmetric and, for ``floor > 0``, strictly positive definite -- a bad raw
    scale (an all-zero or blown-up input) cannot propagate into a downstream
    Cholesky failure.
    """
    symmetric = symmetrize(matrix)
    eigenvalues, eigenvectors = np.linalg.eigh(symmetric)
    clamped = np.clip(eigenvalues, floor, ceiling)
    return symmetrize(eigenvectors @ np.diag(clamped) @ eigenvectors.T)


def is_spd(matrix: FloatArray, *, floor: float = 0.0) -> bool:
    """True when ``matrix`` is symmetric and every eigenvalue exceeds ``floor``."""
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        return False
    if not np.allclose(matrix, matrix.T, atol=1e-8):
        return False
    eigenvalues = np.linalg.eigvalsh(symmetrize(matrix))
    return bool(np.all(eigenvalues > floor))


def whitening_frame(metric_tensor: FloatArray) -> FloatArray:
    """Return the orthonormal local frame (whitening basis) for ``metric_tensor``.

    ``metric_tensor`` MUST already be SPD (callers clamp before this point).
    The frame ``F`` satisfies ``F @ metric_tensor @ F.T == I``: it is the
    basis in which the metric looks Euclidean, i.e. the local frame Semantic
    Projection places coordinates in.
    """
    cholesky_lower = np.linalg.cholesky(symmetrize(metric_tensor))
    return np.asarray(np.linalg.inv(cholesky_lower.T), dtype=np.float64)


def to_matrix_tuple(matrix: FloatArray | Matrix) -> Matrix:
    return tuple(tuple(float(x) for x in row) for row in matrix)


def to_vector_tuple(vector: FloatArray | Vector) -> Vector:
    return tuple(float(x) for x in vector)


def matrix_array(matrix: Matrix) -> FloatArray:
    """Reconstruct a mutable ``ndarray`` view from a frozen ``Matrix`` tuple.

    ABI dataclasses store ``Matrix``/``Vector`` (immutable, RFC-MM002 SS4.2
    Defensive Tuple Locking); linear-algebra code converts back to ``ndarray``
    on demand at the point of use rather than holding a mutable array field.
    """
    return np.asarray(matrix, dtype=np.float64)


def freeze_matrix(value: Any) -> Matrix:
    """Defensive-copy + freeze any array-like 2D input into a ``Matrix`` tuple.

    Idempotent: freezing an already-frozen ``Matrix`` reconstructs an equal
    tuple. Called from ``__post_init__`` on every ABI dataclass that carries a
    2D field, so construction is the sole defensive-copy boundary regardless
    of whether the caller passed an ``ndarray`` or a plain nested sequence.
    """
    return tuple(tuple(float(x) for x in row) for row in value)
