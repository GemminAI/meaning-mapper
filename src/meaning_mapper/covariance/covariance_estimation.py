"""Stage 5: Covariance Estimation.

Sigma = sigma_input^2 * (B @ B.T) per RFC-MM003 SS4 ("Uncertainty Covariance
Propagation"), where ``B`` is the Local Frame's whitening basis. The
whitening frame satisfies ``B @ g @ B.T == I`` by construction (Local Frame
Resolution), which means ``B @ B.T == g^-1`` exactly -- so this is the same
"metric inverse scaled by 1/density" quantity Covariance Estimation always
produced, re-derived from ``B`` instead of the metric tensor directly to
match RFC-MM003's canonical form. ``sigma_input^2 := 1 / density.value``
(sparse evidence widens the reported uncertainty, dense evidence narrows it,
same as before); see ``docs/RFC_ALIGNMENT.md`` SS3.3 for the derivation and
for why RFC-MM003 leaves ``sigma_input^2``'s source unspecified.

``B`` is guaranteed invertible by Local Frame Resolution, so ``B @ B.T`` is
guaranteed SPD before the eigenvalue clamp below even runs -- ``validate()``
exists as the boundary check for callers that did not go through
``estimate_covariance``, not because this function can silently emit a
broken matrix.
"""

from __future__ import annotations

from dataclasses import dataclass

from meaning_mapper._constants import SIGMA_EIGEN_CEILING, SIGMA_EIGEN_FLOOR
from meaning_mapper._linalg import (
    FloatArray,
    Matrix,
    clamp_eigenvalues,
    freeze_matrix,
    is_spd,
    matrix_array,
)
from meaning_mapper.density.density_estimation import Density
from meaning_mapper.errors import InvariantError
from meaning_mapper.frame.local_frame import LocalFrame


@dataclass(frozen=True, slots=True)
class Covariance:
    """A local SPD covariance (uncertainty) matrix, Sigma."""

    matrix: Matrix

    def __post_init__(self) -> None:
        object.__setattr__(self, "matrix", freeze_matrix(self.matrix))

    @property
    def array(self) -> FloatArray:
        """The mutable ``ndarray`` view, reconstructed on demand for math."""
        return matrix_array(self.matrix)

    def validate(self) -> None:
        if not is_spd(self.array):
            raise InvariantError("covariance matrix is not symmetric positive-definite")


def estimate_covariance(frame: LocalFrame, density: Density) -> Covariance:
    basis = frame.array
    sigma_input_squared = 1.0 / density.value
    raw = sigma_input_squared * (basis @ basis.T)
    clamped = clamp_eigenvalues(raw, SIGMA_EIGEN_FLOOR, SIGMA_EIGEN_CEILING)
    return Covariance(matrix=freeze_matrix(clamped))
