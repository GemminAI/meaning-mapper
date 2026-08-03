# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""RFC-SA002 AnnotationView — frozen, domain-neutral ABI snapshot."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AnnotationView:
    """Sovereign domain-neutral schema defined by RFC-SA002.

    Absolutely clean of runtime, framework, or communication dependencies.
    """

    version: str = "1.0"
    annotation_id: str = ""
    source_type: str = ""
    coordinates: tuple[float, ...] = field(default_factory=tuple)
    semantic_density: float = 0.0
    payload_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_wire(self) -> dict[str, Any]:
        """Serialize to the SA005 response layout (primitives only)."""
        return {
            "schema_id": self.payload_snapshot.get(
                "schema_id", "urn:gemminai:schema:sa003:1.0"
            ),
            "version": self.version,
            "annotation_id": self.annotation_id,
            "source_type": self.source_type,
            "coordinates": list(self.coordinates),
            "semantic_density": self.semantic_density,
            "payload_snapshot": dict(self.payload_snapshot),
        }
