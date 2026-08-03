# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""RFC-SA004 / SA005 Runtime Bridge — sole DTO + transport confinement zone.

AST RULE: RuntimeAnnotationDTO and runtime.* types MUST remain in this module.
httpx / requests imports are legal ONLY here (and the HTTP service entrypoint).
"""

from __future__ import annotations

import copy
import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

from meaning_mapper.abi.annotation_view import AnnotationView
from meaning_mapper.payload.schema import (
    SCHEMA_ID,
    SchemaValidationError,
    clamp_density,
    normalize_payload,
)

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]


@dataclass
class RuntimeAnnotationDTO:
    """Mutable runtime-owned DTO. Confined to this module (RFC-SA002 §2.1)."""

    version: str = "1.0"
    annotation_id: str = ""
    source_type: str = ""
    coordinates: list[float] = field(default_factory=list)
    semantic_density: float | str = 0.0
    payload_snapshot: dict[str, Any] = field(default_factory=dict)
    # Spec-external fields may appear at runtime; Ignore Unknowns applies.
    future_extension_tag: Any = None


class RuntimeBridge(Protocol):
    """Sovereign interface for runtime bridging (RFC-SA002 §5)."""

    def bridge_annotation(self, raw_dto: Any) -> AnnotationView: ...


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coords_tuple(raw_coords: Any) -> tuple[float, ...]:
    if raw_coords is None:
        return ()
    try:
        return tuple(float(x) for x in raw_coords)
    except (TypeError, ValueError):
        return ()


def _defensive_payload_copy(raw_payload: Any) -> dict[str, Any]:
    """Single copy boundary: shallow if flat primitives, deep if nested mutables."""
    if not isinstance(raw_payload, dict):
        return {}
    nested = any(isinstance(v, (dict, list)) for v in raw_payload.values())
    if nested:
        return copy.deepcopy(raw_payload)
    return dict(raw_payload)


def dto_from_mapping(raw: dict[str, Any]) -> RuntimeAnnotationDTO:
    """Build a RuntimeAnnotationDTO from a JSON object (unknowns kept only on DTO)."""
    return RuntimeAnnotationDTO(
        version=str(raw.get("version", "1.0")),
        annotation_id=str(raw.get("annotation_id", "")),
        source_type=str(raw.get("source_type", "")),
        coordinates=list(raw.get("coordinates") or []),
        semantic_density=raw.get("semantic_density", 0.0),  # type: ignore[arg-type]
        payload_snapshot=dict(raw.get("payload_snapshot") or {})
        if isinstance(raw.get("payload_snapshot"), dict)
        else {},
        future_extension_tag=raw.get("future_extension_tag"),
    )


class StandardRuntimeBridge:
    """Sovereign implementation of RFC-SA004 / RFC-SA002."""

    def bridge_annotation(self, raw_dto: Any) -> AnnotationView:
        if raw_dto is None:
            return AnnotationView()

        if isinstance(raw_dto, dict):
            raw_dto = dto_from_mapping(raw_dto)

        coords_tuple = _coords_tuple(getattr(raw_dto, "coordinates", None) or ())

        density = clamp_density(
            _safe_float(getattr(raw_dto, "semantic_density", 0.0), 0.0)
        )

        raw_payload = getattr(raw_dto, "payload_snapshot", None)
        payload_snapshot = _defensive_payload_copy(raw_payload)

        # Validate / normalize SA003 headers when present; drop on hard failure.
        if payload_snapshot:
            try:
                # Flat SA005 style embeds vocab in payload_snapshot; ensure schema headers.
                if "schema_id" not in payload_snapshot:
                    payload_snapshot = {
                        "schema_id": SCHEMA_ID,
                        "payload_class": payload_snapshot.get("payload_class", "hybrid"),
                        "generator_signature": payload_snapshot.get(
                            "generator_signature", "unknown"
                        ),
                        "data": {
                            k: v
                            for k, v in payload_snapshot.items()
                            if k
                            not in {
                                "schema_id",
                                "payload_class",
                                "generator_signature",
                                "data",
                            }
                        },
                    }
                normalized = normalize_payload(payload_snapshot)
                # Store normalized SA003 envelope in the snapshot for domain consumers.
                payload_snapshot = {
                    "schema_id": normalized["schema_id"],
                    "payload_class": normalized["payload_class"],
                    "generator_signature": normalized["generator_signature"],
                    **normalized["data"],
                }
                if "semantic_density" in normalized["data"]:
                    density = clamp_density(
                        float(normalized["data"]["semantic_density"])
                    )
                elif "confidence" in normalized["data"]:
                    from meaning_mapper.payload.schema import compute_semantic_density

                    density = compute_semantic_density(
                        normalized["data"]["confidence"],
                        entropy=normalized["data"].get("drift_index", 0.0),
                    )
            except SchemaValidationError:
                # Fail-fast drop → neutral view (Principle 5 optional)
                return AnnotationView()

        # Prefer coordinates from payload spatial data when view coords empty.
        if not coords_tuple and isinstance(payload_snapshot.get("coordinates"), list):
            coords_tuple = _coords_tuple(payload_snapshot.get("coordinates"))

        version = str(getattr(raw_dto, "version", "1.0"))
        annotation_id = str(getattr(raw_dto, "annotation_id", ""))
        source_type = str(getattr(raw_dto, "source_type", ""))

        return AnnotationView(
            version=version,
            annotation_id=annotation_id,
            source_type=source_type,
            coordinates=coords_tuple,
            semantic_density=density,
            payload_snapshot=payload_snapshot,
        )


class ReplayRuntimeBridge:
    """Deterministic offline replay from a JSON file (RFC-SA004 §5)."""

    def __init__(self, path: str | Path, bridge: RuntimeBridge | None = None) -> None:
        self.path = Path(path)
        self._bridge = bridge or StandardRuntimeBridge()

    def bridge_annotation(self, raw_dto: Any = None) -> AnnotationView:
        if raw_dto is not None:
            return self._bridge.bridge_annotation(raw_dto)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return self._bridge.bridge_annotation(data)


class HTTPRuntimeBridge:
    """RFC-SA005 HTTP transport client — never raises network exceptions outward."""

    def __init__(
        self,
        endpoint_url: str,
        api_key: str = "",
        timeout_seconds: float = 3.0,
        *,
        client_id: str = "gemminai-exp5000-node-01",
        max_attempts: int = 5,
        t0: float = 1.0,
        t_max: float = 16.0,
        sleep_fn: Any = None,
        transport: Any = None,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.headers = {
            "Authorization": f"Bearer {api_key}" if api_key else "",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-GemminAI-Client": "EXP-5000-Core",
        }
        if not api_key:
            self.headers.pop("Authorization", None)
        self.timeout = timeout_seconds
        self.client_id = client_id
        self.max_attempts = max_attempts
        self.t0 = t0
        self.t_max = t_max
        self._sleep = sleep_fn or time.sleep
        self._transport = transport
        self._inner = StandardRuntimeBridge()
        self.last_attempts = 0
        self.last_wait_times: list[float] = []

    def bridge_annotation(self, raw_dto: Any) -> AnnotationView:
        return self._inner.bridge_annotation(raw_dto)

    def fetch_and_bridge(
        self,
        observation_id: str,
        prompt_id: str,
        raw_data: dict[str, Any],
        *,
        timestamp: str | None = None,
    ) -> AnnotationView:
        if httpx is None:
            return AnnotationView()

        request_payload: dict[str, Any] = {
            "client_id": self.client_id,
            "observation_id": observation_id,
            "prompt_id": prompt_id,
            "raw_observational_data": raw_data,
        }
        if timestamp:
            request_payload["timestamp"] = timestamp

        wait_time = self.t0
        self.last_attempts = 0
        self.last_wait_times = []

        parsed = urlparse(self.endpoint_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else self.endpoint_url
        path = parsed.path or "/api/v1/annotate"

        for attempt in range(self.max_attempts):
            self.last_attempts = attempt + 1
            try:
                client_kwargs: dict[str, Any] = {
                    "headers": self.headers,
                    "timeout": self.timeout,
                    "base_url": base_url,
                }
                if self._transport is not None:
                    client_kwargs["transport"] = self._transport
                with httpx.Client(**client_kwargs) as client:
                    response = client.post(path, json=request_payload)

                    if response.status_code == 200:
                        return self._bridge_json_to_view(response.json())

                    if response.status_code == 429:
                        retry_after = response.headers.get("Retry-After")
                        if retry_after and str(retry_after).replace(".", "", 1).isdigit():
                            sleep_sec = float(retry_after)
                        else:
                            sleep_sec = self._backoff_with_jitter(attempt, wait_time)
                            wait_time = min(self.t_max, wait_time * 2.0)
                        self.last_wait_times.append(sleep_sec)
                        self._sleep(sleep_sec)
                        continue

                    if response.status_code >= 500:
                        sleep_sec = self._backoff_with_jitter(attempt, wait_time)
                        self.last_wait_times.append(sleep_sec)
                        self._sleep(sleep_sec)
                        wait_time = min(self.t_max, wait_time * 2.0)
                        continue

                    # 4xx: fail-fast, no retry
                    return AnnotationView()

            except httpx.HTTPError:
                # Connect/timeout/transport rupture — retry then neutral fallback
                sleep_sec = self._backoff_with_jitter(attempt, wait_time)
                self.last_wait_times.append(sleep_sec)
                self._sleep(sleep_sec)
                wait_time = min(self.t_max, wait_time * 2.0)
                continue
            except (TypeError, ValueError, KeyError):
                return AnnotationView()

        return AnnotationView()

    def _backoff_with_jitter(self, n: int, base: float) -> float:
        """T_n = min(T_max, T_0 * 2^n ± uniform(0, J)), J = 0.2 * T_0 * 2^n."""
        nominal = min(self.t_max, self.t0 * (2**n))
        jitter_width = 0.2 * self.t0 * (2**n)
        jitter = random.uniform(-jitter_width, jitter_width)
        return max(0.0, min(self.t_max, nominal + jitter))

    def _bridge_json_to_view(self, raw_json: dict[str, Any]) -> AnnotationView:
        return self._inner.bridge_annotation(raw_json)
