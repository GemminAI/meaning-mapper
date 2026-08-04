"""Private SPD-matrix helpers shared by the metric/frame/covariance stages.

Not part of the public API. Every function here is pure and deterministic:
same input array, same output, every time.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


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


def to_matrix_tuple(matrix: FloatArray) -> tuple[tuple[float, ...], ...]:
    return tuple(tuple(float(x) for x in row) for row in matrix)


def to_vector_tuple(vector: FloatArray) -> tuple[float, ...]:
    return tuple(float(x) for x in vector)
