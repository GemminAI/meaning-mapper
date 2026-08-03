# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""Replaceable annotator engine protocol (RFC-SA001 Principle 4)."""

from __future__ import annotations

from typing import Any, Protocol


class AnnotatorEngine(Protocol):
    """Produces an SA005 wire annotation from a measured observation."""

    def annotate(
        self,
        *,
        observation_id: str,
        prompt_id: str,
        raw_observational_data: dict[str, Any],
        client_id: str = "",
        timestamp: str | None = None,
    ) -> dict[str, Any]: ...
