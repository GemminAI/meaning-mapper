"""Stage 3: Local Frame Resolution.

Turns the metric tensor into an orthonormal local frame (a whitening basis):
the coordinate system Semantic Projection places ``theta`` in. When an
observation carries no informative content (all-zero raw features, or any
matrix Cholesky rejects despite upstream clamping) resolution bootstraps the
canonical identity frame rather than failing -- there being "nothing local
yet" is itself a valid, reproducible frame, not an error.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from meaning_mapper._constants import DEFAULT_FRAME_ID
from meaning_mapper._linalg import FloatArray, Matrix, freeze_matrix, matrix_array, whitening_frame
from meaning_mapper.metrics.metric_tensor import MetricTensor


@dataclass(frozen=True, slots=True)
class LocalFrame:
    """An orthonormal local frame: ``basis @ g @ basis.T == I``.

    ``basis`` and ``metric_tensor`` are frozen ``Matrix`` tuples (RFC-MM002
    Defensive Tuple Locking, see :class:`~meaning_mapper.metrics.metric_tensor.MetricTensor`).
    ``ambient_dim``/``semantic_dim`` (RFC-MM002 SS2.2) are derived properties
    rather than stored fields: this implementation's projection is a full-rank
    whitening map (no dimensionality reduction), so the two are always equal
    to ``metric_tensor``'s and ``basis``'s row count respectively and cannot
    drift out of sync with the matrices they describe.
    """

    basis: Matrix
    metric_tensor: Matrix
    bootstrapped: bool
    frame_id: str = DEFAULT_FRAME_ID

    def __post_init__(self) -> None:
        object.__setattr__(self, "basis", freeze_matrix(self.basis))
        object.__setattr__(self, "metric_tensor", freeze_matrix(self.metric_tensor))

    @property
    def dimension(self) -> int:
        return len(self.basis)

    @property
    def ambient_dim(self) -> int:
        return len(self.metric_tensor)

    @property
    def semantic_dim(self) -> int:
        return len(self.basis)

    @property
    def array(self) -> FloatArray:
        """The mutable ``ndarray`` view of ``basis``, reconstructed on demand."""
        return matrix_array(self.basis)


def resolve_local_frame(
    metric_tensor: MetricTensor, *, frame_id: str = DEFAULT_FRAME_ID
) -> LocalFrame:
    try:
        basis = whitening_frame(metric_tensor.array)
    except np.linalg.LinAlgError:
        return LocalFrame(
            basis=freeze_matrix(np.eye(metric_tensor.dimension)),
            metric_tensor=metric_tensor.matrix,
            bootstrapped=True,
            frame_id=frame_id,
        )
    return LocalFrame(
        basis=freeze_matrix(basis),
        metric_tensor=metric_tensor.matrix,
        bootstrapped=False,
        frame_id=frame_id,
    )
