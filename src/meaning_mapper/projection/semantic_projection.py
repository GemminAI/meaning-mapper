"""Stage 6: Semantic Projection.

Projects a HEXT Observation's raw features into local semantic coordinates
``theta``, using the local frame already resolved by the earlier stages.
This is a fixed, purely geometric operation: ``theta = frame.basis @
raw_features``, placing the raw feature vector in the whitening frame so
that distances in the result are Euclidean distances under the metric
tensor estimated for this observation's own neighborhood.

Semantic Projection is deliberately *not* an extension seam toward functors,
natural transformations, pullbacks, pushouts, or other categorical-theory
machinery -- that is Categorical Lift, owned by the independent Categorical
Lift Engine (CLE), not Meaning Mapper. See ``docs/BOUNDARIES.md``. Meaning
Mapper's projection stops at a single position-plus-uncertainty measurement;
it does not interpret trajectories, discover concepts, or touch HEKB.
"""

from __future__ import annotations

from meaning_mapper._linalg import FloatArray, to_vector_tuple
from meaning_mapper.frame.local_frame import LocalFrame


def project_to_theta(raw_features: FloatArray, frame: LocalFrame) -> tuple[float, ...]:
    """Project ``raw_features`` through ``frame`` into local semantic coordinates."""
    return to_vector_tuple(frame.basis @ raw_features)
