"""Stage 6: Categorical Lift.

The MM-internal stage that projects a HEXT Observation's raw features into
local semantic coordinates ``theta``, using the local frame and evidence
already resolved by the earlier stages. It is not a separate engine, module,
or repository -- Categorical Lift is an implementation detail of Meaning
Mapper's measurement pipeline (see ``docs/BOUNDARIES.md``: no ``cle/``,
``categorical-lift/``, or "CLE Engine" exists).

``CategoricalLift`` is a :class:`typing.Protocol` so the initial deterministic
linear projection can later be swapped for something built from actual
categorical-theory machinery -- a functor between the raw-feature and
meaning-space categories, a natural transformation between two lift
strategies, or a pullback/pushout/commutative-diagram construction over
several frames -- without changing any other stage's contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from meaning_mapper._linalg import FloatArray, to_vector_tuple
from meaning_mapper.frame.local_frame import LocalFrame


class CategoricalLift(Protocol):
    """The extension seam: anything satisfying this shape can lift."""

    def lift(self, raw_features: FloatArray, frame: LocalFrame) -> FloatArray: ...


@dataclass(frozen=True, slots=True)
class DeterministicLinearLift:
    """The initial implementation: ``theta = frame.basis @ raw_features``.

    Placing the raw feature vector in the whitening frame is exactly what
    makes the result a set of *local semantic coordinates*: distances in
    this basis are Euclidean distances under the metric tensor the earlier
    stages estimated for this observation's own neighborhood.
    """

    def lift(self, raw_features: FloatArray, frame: LocalFrame) -> FloatArray:
        return frame.basis @ raw_features


default_lift = DeterministicLinearLift()


def lift_to_theta(
    raw_features: FloatArray,
    frame: LocalFrame,
    lift: CategoricalLift = default_lift,
) -> tuple[float, ...]:
    """Run ``lift`` and return theta as the plain tuple MeaningMeasurement carries."""
    return to_vector_tuple(lift.lift(raw_features, frame))
