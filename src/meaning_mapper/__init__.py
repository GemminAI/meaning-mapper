"""Meaning Mapper — the SensOS Meaning Measurement engine.

Boundary: HEXT Observation in, MeaningMeasurement out. Meaning Mapper
measures; it does not hold runtime state, control anything, or render
language. See ``docs/BOUNDARIES.md``.
"""

from __future__ import annotations

from meaning_mapper.errors import QuarantineReason
from meaning_mapper.measurement.meaning_measurement import MeaningMeasurement
from meaning_mapper.pipeline import MeasurementResult, map_observation
from meaning_mapper.version import __version__

__all__ = [
    "MeaningMeasurement",
    "MeasurementResult",
    "QuarantineReason",
    "__version__",
    "map_observation",
]
