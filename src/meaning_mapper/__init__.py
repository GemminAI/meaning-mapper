# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""Meaning Mapper — reference service for observation → HEXT meaning projection."""

from __future__ import annotations

from meaning_mapper.version import __version__

__all__ = ["__version__", "map_observation"]


def map_observation(*args, **kwargs):
    """Map a raw observation into a HEXT Observation Object.

    Thin product-facing alias over the Semantic Annotator Core reference library.
    """
    from semantic_annotator.pipeline import annotate

    return annotate(*args, **kwargs)
