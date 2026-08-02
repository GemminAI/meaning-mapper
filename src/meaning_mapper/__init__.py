# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""Meaning Mapper — SensOS Open Standards Reference Service (RFC-SA001–SA005)."""

from __future__ import annotations

from meaning_mapper.abi.annotated_observation import AnnotatedObservation
from meaning_mapper.abi.annotation_view import AnnotationView
from meaning_mapper.mapper.annotation_mapper import map_annotation
from meaning_mapper.version import __version__

__all__ = [
    "AnnotatedObservation",
    "AnnotationView",
    "__version__",
    "map_annotation",
]
