from __future__ import annotations

import numpy as np

from meaning_mapper._linalg import FloatArray
from meaning_mapper.frame.local_frame import LocalFrame
from meaning_mapper.lift.categorical_lift import (
    DeterministicLinearLift,
    default_lift,
    lift_to_theta,
)


def test_deterministic_linear_lift_projects_through_frame_basis() -> None:
    frame = LocalFrame(basis=np.diag([2.0, 3.0]), bootstrapped=False)
    raw = np.array([1.0, 1.0])
    result = DeterministicLinearLift().lift(raw, frame)
    assert np.allclose(result, np.array([2.0, 3.0]))


def test_lift_to_theta_uses_default_lift_and_returns_plain_tuple() -> None:
    frame = LocalFrame(basis=np.eye(3), bootstrapped=False)
    raw = np.array([1.0, 2.0, 3.0])
    theta = lift_to_theta(raw, frame)
    assert theta == (1.0, 2.0, 3.0)
    assert all(isinstance(x, float) for x in theta)


def test_lift_to_theta_accepts_a_custom_categorical_lift() -> None:
    class DoublingLift:
        def lift(self, raw_features: FloatArray, frame: LocalFrame) -> FloatArray:
            return 2.0 * (frame.basis @ raw_features)

    frame = LocalFrame(basis=np.eye(2), bootstrapped=False)
    raw = np.array([1.0, 5.0])
    theta = lift_to_theta(raw, frame, DoublingLift())
    assert theta == (2.0, 10.0)


def test_default_lift_is_a_deterministic_linear_lift() -> None:
    assert isinstance(default_lift, DeterministicLinearLift)
