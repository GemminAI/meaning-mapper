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

from meaning_mapper._linalg import FloatArray, whitening_frame
from meaning_mapper.metrics.metric_tensor import MetricTensor


@dataclass(frozen=True, slots=True)
class LocalFrame:
    """An orthonormal local frame: ``basis @ g @ basis.T == I``."""

    basis: FloatArray
    bootstrapped: bool

    @property
    def dimension(self) -> int:
        return int(self.basis.shape[0])


def resolve_local_frame(metric_tensor: MetricTensor) -> LocalFrame:
    try:
        basis = whitening_frame(metric_tensor.matrix)
    except np.linalg.LinAlgError:
        return LocalFrame(basis=np.eye(metric_tensor.dimension), bootstrapped=True)
    return LocalFrame(basis=basis, bootstrapped=False)
