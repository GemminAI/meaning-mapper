from __future__ import annotations

import numpy as np

from meaning_mapper._linalg import (
    clamp_eigenvalues,
    is_spd,
    symmetrize,
    to_matrix_tuple,
    to_vector_tuple,
    whitening_frame,
)


def test_symmetrize_averages_asymmetry() -> None:
    matrix = np.array([[1.0, 2.0], [0.0, 1.0]])
    result = symmetrize(matrix)
    assert np.allclose(result, result.T)
    assert np.allclose(result, np.array([[1.0, 1.0], [1.0, 1.0]]))


def test_clamp_eigenvalues_floors_and_ceils() -> None:
    matrix = np.diag([1e-9, 1e9])
    clamped = clamp_eigenvalues(matrix, floor=1e-3, ceiling=1e3)
    eigenvalues = np.linalg.eigvalsh(clamped)
    assert np.all(eigenvalues >= 1e-3 - 1e-9)
    assert np.all(eigenvalues <= 1e3 + 1e-6)


def test_clamp_eigenvalues_leaves_well_scaled_matrix_symmetric() -> None:
    matrix = np.diag([1.0, 2.0, 3.0])
    clamped = clamp_eigenvalues(matrix, floor=1e-6, ceiling=1e6)
    assert np.allclose(clamped, clamped.T)


def test_is_spd_true_for_identity() -> None:
    assert is_spd(np.eye(4))


def test_is_spd_false_for_non_square() -> None:
    assert not is_spd(np.ones((2, 3)))


def test_is_spd_false_for_asymmetric() -> None:
    matrix = np.array([[1.0, 2.0], [0.0, 1.0]])
    assert not is_spd(matrix)


def test_is_spd_false_below_floor() -> None:
    matrix = np.diag([1.0, 0.0])
    assert not is_spd(matrix, floor=0.0)
    assert not is_spd(matrix, floor=0.5)


def test_whitening_frame_normalizes_metric_to_identity() -> None:
    metric = np.diag([4.0, 9.0])
    frame = whitening_frame(metric)
    assert np.allclose(frame @ metric @ frame.T, np.eye(2), atol=1e-8)


def test_to_matrix_tuple_and_vector_tuple_are_plain_floats() -> None:
    matrix = np.array([[1, 2], [3, 4]])
    vector = np.array([1, 2, 3])
    matrix_tuple = to_matrix_tuple(matrix)
    vector_tuple = to_vector_tuple(vector)
    assert matrix_tuple == ((1.0, 2.0), (3.0, 4.0))
    assert vector_tuple == (1.0, 2.0, 3.0)
    assert all(isinstance(x, float) for row in matrix_tuple for x in row)
    assert all(isinstance(x, float) for x in vector_tuple)
