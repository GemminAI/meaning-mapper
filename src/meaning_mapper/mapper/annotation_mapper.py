# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""RFC-SA001 / SA002 Annotation Mapper — domain-side, no second copy."""

from __future__ import annotations

from meaning_mapper.abi.annotated_observation import AnnotatedObservation
from meaning_mapper.abi.annotation_view import AnnotationView


def map_annotation(
    prompt_id: str,
    view: AnnotationView,
    *,
    observation_id: str = "",
) -> AnnotatedObservation:
    """Lift a trusted AnnotationView into AnnotatedObservation.

    RFC-SA002 §4.1: NO defensive re-copy. The view is already domain-owned.
    """
    return AnnotatedObservation(
        observation_id=observation_id,
        prompt_id=prompt_id,
        view=view,
    )


class AnnotationMapper:
    """Callable mapper object for dependency injection."""

    def map(
        self,
        prompt_id: str,
        view: AnnotationView,
        *,
        observation_id: str = "",
    ) -> AnnotatedObservation:
        return map_annotation(prompt_id, view, observation_id=observation_id)
