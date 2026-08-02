# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""Meaning Mapper HTTP reference service."""

from __future__ import annotations

from typing import Any

from adapters import list_adapters
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from semantic_annotator.pipeline import annotate
from validation import ValidationError

from meaning_mapper.version import __version__

app = FastAPI(
    title="Meaning Mapper",
    version=__version__,
    description=(
        "Reference service that maps raw observations into HEXT Observation Objects. "
        "Deterministic. Stateless. Aligned with SensOS Open Standards. "
        "No storage, reasoning, LLM inference, or enterprise runtime control."
    ),
)


class MapRequest(BaseModel):
    document: Any = Field(..., description="Raw observation (string, object, or array)")
    source_type: str | None = None
    source_ref: str | None = None
    filename: str | None = None


def _map(body: MapRequest) -> dict[str, Any]:
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "meaning-mapper", "version": __version__}


@app.get("/adapters")
def adapters() -> dict[str, list[str]]:
    return {"adapters": list_adapters()}


@app.post("/map")
def map_endpoint(body: MapRequest) -> dict[str, Any]:
    """Canonical Meaning Mapper endpoint."""
    return _map(body)


@app.post("/annotate", deprecated=True)
def annotate_compat(body: MapRequest) -> dict[str, Any]:
    """Deprecated compatibility alias for Semantic Annotator Core clients.

    Prefer ``POST /map``.
    """
    return _map(body)


def create_app() -> FastAPI:
    return app
