"""Tunable constants for the deterministic measurement pipeline.

Kept in one place so clamp bands (the recurring "raw-scale blew up the
downstream matrix" failure mode) are reviewable at a glance.
"""

from __future__ import annotations

MEANING_SPACE_DIMENSION = 8

# Metric Tensor Estimation: eigenvalue band for g.
METRIC_EIGEN_FLOOR = 1.0e-3
METRIC_EIGEN_CEILING = 1.0e3

# Density Estimation: clamp band for the local density scalar.
DENSITY_FLOOR = 1.0e-3
DENSITY_CEILING = 1.0e3

# Covariance Estimation: eigenvalue band for Sigma.
SIGMA_EIGEN_FLOOR = 1.0e-6
SIGMA_EIGEN_CEILING = 1.0e6

# Topological Consistency Check: theta must land within
# THETA_BOUND_SCALE * sqrt(trace(sigma)) of the origin to be considered
# self-consistent with its own reported uncertainty.
THETA_BOUND_SCALE = 50.0

DEFAULT_FRAME_ID = "meaning-mapper.default"
