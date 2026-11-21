"""Measure a window's rows in a caller-supplied frame. Nothing is stored."""

from __future__ import annotations

from meaning_mapper.window.measure import (
    WindowFrame,
    WindowMeasureError,
    WindowMeasurement,
    frame_content_id,
    measure_window,
    window_rows,
)

__all__ = [
    "WindowFrame",
    "WindowMeasureError",
    "WindowMeasurement",
    "frame_content_id",
    "measure_window",
    "window_rows",
]
