# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""Domain-owned AnnotatedObservation (RFC-SA001 / SA002)."""

from __future__ import annotations

from dataclasses import dataclass

from meaning_mapper.abi.annotation_view import AnnotationView


@dataclass(frozen=True)
class AnnotatedObservation:
    """Measured observation identity + trusted AnnotationView.

    Ownership: domain. Built only via AnnotationMapper after the SA-002 boundary.
    """

    observation_id: str
    prompt_id: str
    view: AnnotationView
