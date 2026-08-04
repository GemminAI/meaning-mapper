from __future__ import annotations

import numpy as np

from meaning_mapper.frame.local_frame import LocalFrame
from meaning_mapper.projection.semantic_projection import project_to_theta


def test_project_to_theta_projects_through_frame_basis() -> None:
    frame = LocalFrame(basis=np.diag([2.0, 3.0]), metric_tensor=np.eye(2), bootstrapped=False)
    raw = np.array([1.0, 1.0])
    theta = project_to_theta(raw, frame)
    assert theta == (2.0, 3.0)


def test_project_to_theta_returns_plain_float_tuple() -> None:
    frame = LocalFrame(basis=np.eye(3), metric_tensor=np.eye(3), bootstrapped=False)
    raw = np.array([1.0, 2.0, 3.0])
    theta = project_to_theta(raw, frame)
    assert theta == (1.0, 2.0, 3.0)
    assert all(isinstance(x, float) for x in theta)


def test_project_to_theta_is_deterministic() -> None:
    frame = LocalFrame(basis=np.diag([2.0, 5.0]), metric_tensor=np.eye(2), bootstrapped=False)
    raw = np.array([3.0, 4.0])
    first = project_to_theta(raw, frame)
    second = project_to_theta(raw, frame)
    assert first == second
