"""HTTP-only adapter to the independent CLE service.

Meaning Mapper does not import `cle` -- same convention already used at
this repo's other boundaries (`types.py`: "Meaning Mapper does not import
semantic-annotator-core or msr"). This client only speaks JSON over HTTP
(httpx) against endpoints confirmed live via CLE's own `/openapi.json`
(2026-08-12): `GET /health`, `POST /ground`, `POST /lift`,
`POST /pullback`, `POST /recover`, `POST /compress`.

No CLE algorithm is reimplemented here -- every method is exactly three
steps: build the request payload, send it, parse the response into this
module's own dataclasses (`meaning_mapper.cle.models`). Timeouts and
transport-level failures are normalized to `CLEUnreachableError`; HTTP
error statuses to `CLEHTTPError`; a 200 missing an expected field to
`CLESchemaError` -- three distinct, typed failure modes, not one bare
exception.
"""

from __future__ import annotations

from typing import Any

import httpx

from meaning_mapper.cle.errors import CLEHTTPError, CLEUnreachableError
from meaning_mapper.cle.models import (
    CompressionResult,
    ConceptInput,
    FiniteCategoryInput,
    FiveW1HOverrides,
    GroundResult,
    LiftResult,
    PullbackResult,
    RecoveredContext,
    SOKOverrides,
)


class CLEClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self._client = httpx.Client(base_url=base_url, timeout=timeout_seconds, transport=transport)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> CLEClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def health(self) -> dict[str, Any]:
        response = self._send("GET", "/health")
        self._raise_for_status(response)
        result: dict[str, Any] = response.json()
        return result

    def ground(
        self,
        prompt: str,
        goal: str,
        *,
        five_w1h_overrides: FiveW1HOverrides | None = None,
        sok_overrides: SOKOverrides | None = None,
        default_knowledge_reference: str = "unspecified",
        embedding_dimension: int = 8,
    ) -> GroundResult:
        payload: dict[str, Any] = {
            "prompt": prompt,
            "goal": goal,
            "default_knowledge_reference": default_knowledge_reference,
            "embedding_dimension": embedding_dimension,
        }
        if five_w1h_overrides is not None:
            payload["five_w1h_overrides"] = five_w1h_overrides.to_payload()
        if sok_overrides is not None:
            payload["sok_overrides"] = sok_overrides.to_payload()
        response = self._send("POST", "/ground", json=payload)
        self._raise_for_status(response)
        return GroundResult.from_payload(response.json())

    def lift(
        self,
        concept: ConceptInput,
        *,
        subject_context: ConceptInput | None = None,
        observer_context: ConceptInput | None = None,
        human_knowledge_context: ConceptInput | None = None,
    ) -> LiftResult:
        payload: dict[str, Any] = {"concept": concept.to_payload()}
        if subject_context is not None:
            payload["subject_context"] = subject_context.to_payload()
        if observer_context is not None:
            payload["observer_context"] = observer_context.to_payload()
        if human_knowledge_context is not None:
            payload["human_knowledge_context"] = human_knowledge_context.to_payload()
        response = self._send("POST", "/lift", json=payload)
        self._raise_for_status(response)
        return LiftResult.from_payload(response.json())

    def pullback(
        self,
        subject: FiniteCategoryInput,
        observer: FiniteCategoryInput,
        knowledge: FiniteCategoryInput,
    ) -> PullbackResult:
        payload = {
            "subject": subject.to_payload(),
            "observer": observer.to_payload(),
            "knowledge": knowledge.to_payload(),
        }
        response = self._send("POST", "/pullback", json=payload)
        self._raise_for_status(response)
        return PullbackResult.from_payload(response.json())

    def recover(
        self, subject: ConceptInput, observer: ConceptInput, knowledge: ConceptInput
    ) -> RecoveredContext:
        """Requires the CLE composition root to have wired a
        `recovery_engine` -- the default CLE app instance returns 503
        (`CLEHTTPError(status_code=503, ...)`) otherwise. Not this
        adapter's concern to work around; that is CLE deployment
        configuration."""
        payload = {
            "subject": subject.to_payload(),
            "observer": observer.to_payload(),
            "knowledge": knowledge.to_payload(),
        }
        response = self._send("POST", "/recover", json=payload)
        self._raise_for_status(response)
        return RecoveredContext.from_payload(response.json())

    def compress(self, raw_context: Any, lifted_morphism_set: Any) -> CompressionResult:
        payload = {"raw_context": raw_context, "lifted_morphism_set": lifted_morphism_set}
        response = self._send("POST", "/compress", json=payload)
        self._raise_for_status(response)
        return CompressionResult.from_payload(response.json())

    def _send(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        try:
            return self._client.request(method, url, **kwargs)
        except httpx.TransportError as exc:
            raise CLEUnreachableError(f"CLE unreachable: {exc}") from exc

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        body: Any
        try:
            body = response.json()
        except ValueError:
            body = response.text
        raise CLEHTTPError(response.status_code, body)


__all__ = ["CLEClient"]
