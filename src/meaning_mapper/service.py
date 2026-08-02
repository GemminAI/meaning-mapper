# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""Meaning Mapper HTTP reference service — RFC-SA005 transport surface."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from meaning_mapper.engine.deterministic import DeterministicAnnotatorEngine
from meaning_mapper.engine.protocol import AnnotatorEngine
from meaning_mapper.runtime_bridge import StandardRuntimeBridge
from meaning_mapper.version import __version__

app = FastAPI(
    title="Meaning Mapper",
    version=__version__,
    description=(
        "SensOS Open Standards Reference Service for semantic annotation "
        "(RFC-SA001–SA005). Deterministic. Model-independent. Stateless. "
        "No NVS-Kernel, HEKB, or commercial runtime orchestration."
    ),
)

_engine: AnnotatorEngine = DeterministicAnnotatorEngine()
_bridge = StandardRuntimeBridge()


class AnnotateRequest(BaseModel):
    """RFC-SA005 request payload."""

    client_id: str = "anonymous"
    observation_id: str
    prompt_id: str = ""
    timestamp: str | None = None
    raw_observational_data: dict[str, Any] = Field(default_factory=dict)


class HextNormalizeRequest(BaseModel):
    """Optional Core library helper — not part of RFC-SA005."""

    document: Any
    source_type: str | None = None
    source_ref: str | None = None
    filename: str | None = None


def set_engine(engine: AnnotatorEngine) -> None:
    """Test/DI hook for replaceable engines (Principle 4)."""
    global _engine
    _engine = engine


def _run_annotate(body: AnnotateRequest) -> dict[str, Any]:
    try:
        wire = _engine.annotate(
            observation_id=body.observation_id,
            prompt_id=body.prompt_id,
            raw_observational_data=body.raw_observational_data,
            client_id=body.client_id,
            timestamp=body.timestamp,
        )
    except (TypeError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # Validate through the sole copy boundary before responding.
    view = _bridge.bridge_annotation(wire)
    return view.to_wire()


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "meaning-mapper",
        "version": __version__,
        "rfc": "SA001-SA005",
    }


@app.post("/api/v1/annotate")
def api_v1_annotate(body: AnnotateRequest) -> dict[str, Any]:
    """RFC-SA005 normative annotation endpoint."""
    return _run_annotate(body)


@app.post("/map")
def map_endpoint(body: AnnotateRequest) -> dict[str, Any]:
    """Canonical Meaning Mapper product entry — SA005 contract."""
    return _run_annotate(body)


@app.post("/annotate", deprecated=True)
def annotate_deprecated(body: AnnotateRequest) -> dict[str, Any]:
    """Deprecated compatibility alias. Prefer POST /map or POST /api/v1/annotate."""
    return _run_annotate(body)


@app.post("/hext/normalize")
def hext_normalize(body: HextNormalizeRequest) -> dict[str, Any]:
    """Optional HEXT normalize via semantic-annotator-core (library RI)."""
    try:
        from semantic_annotator.pipeline import annotate
        from validation import ValidationError
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="semantic-annotator-core unavailable") from exc
    try:
        return annotate(
            body.document,
            source_type=body.source_type,
            source_ref=body.source_ref,
            filename=body.filename,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def create_app() -> FastAPI:
    return app
