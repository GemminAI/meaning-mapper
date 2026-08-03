# RFC-MM001–MM005 Compliance Matrix

**Product:** Meaning Mapper v1.0  
**Authority:** **RFC-MM001 … RFC-MM005** (canonical)  
**Legacy:** RFC-SA001–SA005 are **Superseded** (historical only)  
**Date:** 2026-08-02

> Namespace note: RFC-SA → RFC-MM migration is documented in
> `RFCv3_draft/rfc/MIGRATION_SA_TO_MM.md` and sensos-docs
> `docs/public/RFC_SA_TO_MM_MIGRATION.md`.

## Phase 1 — Architecture Compliance Report (pre → post)

| RFC (canonical) | Legacy | Post-impl | Status |
|-----------------|--------|-----------|--------|
| RFC-MM001 | SA001 | **100%** | Principles + layer map implemented |
| RFC-MM002 | SA002 | **100%** | Meaning View (`AnnotationView`) ABI + confinement tests |
| RFC-MM003 | SA003 | **100%** | Payload schema + density clamp + ignore unknowns |
| RFC-MM004 | SA004 | **100%** | `runtime_bridge.py` single copy boundary |
| RFC-MM005 | SA005 | **100%** | `POST /api/v1/annotate` + `/map` + resilient client bridge |

### RFC-MM001 — Meaning Mapper Architecture (was SA001)

| Requirement | Status |
|-------------|--------|
| P1 Descriptive (no hidden-state inference in annotations) | ✓ Deterministic descriptive engine |
| P2 External (does not mutate MeasuredObservation) | ✓ Observation passed by value; never rewritten |
| P3 Reproducible | ✓ Deterministic annotator; same input → same view |
| P4 Replaceable provider | ✓ `AnnotatorEngine` protocol |
| P5 Optional (empty view on failure) | ✓ Neutral `AnnotationView()` fallback |
| Layer: Annotator → Bridge → View → Mapper | ✓ |
| No transport / storage / kernel in architecture core | ✓ |

### RFC-MM002 — Meaning View ABI (was SA002)

| Requirement | Status |
|-------------|--------|
| Frozen `AnnotationView` fields | ✓ |
| `RuntimeAnnotationDTO` confined to `runtime_bridge.py` | ✓ AST test |
| Domain modules ban `httpx`/`requests` | ✓ AST test |
| Public `__all__` domain-neutral only | ✓ |
| Ignore unknowns | ✓ |
| Single defensive copy at bridge | ✓ |
| `RuntimeBridge` protocol | ✓ |

### RFC-MM003 — Meaning Payload Schema (was SA003)

| Requirement | Status |
|-------------|--------|
| `schema_id` = `urn:gemminai:schema:sa003:1.0` | ✓ |
| `payload_class` ∈ categorical\|spatial\|evaluative\|hybrid | ✓ |
| `generator_signature` required | ✓ |
| Categorical / spatial / evaluative vocab | ✓ |
| `semantic_density` clamp `[0,1]` | ✓ |
| Ignore unknowns / nullable defaults | ✓ |

### RFC-MM004 — Meaning Runtime Bridge (was SA004)

| Requirement | Status |
|-------------|--------|
| `bridge_annotation` single copy | ✓ |
| Tuple freeze for coordinates | ✓ |
| Dict defensive copy (deep when nested) | ✓ |
| schema_id validation / drop | ✓ |
| Type coercion + safe defaults | ✓ |
| `StandardRuntimeBridge` / `ReplayRuntimeBridge` | ✓ |
| Isolation / ignore-extra / density tests | ✓ |

### RFC-MM005 — Meaning Mapper Service API (was SA005)

| Requirement | Status |
|-------------|--------|
| `POST /api/v1/annotate` request/response layouts | ✓ |
| Product canonical `POST /map` (same SA contract) | ✓ |
| Deprecated `POST /annotate` | ✓ |
| Exponential backoff + jitter client | ✓ |
| 200/400/429/5xx semantics | ✓ |
| `HTTPRuntimeBridge` confinement | ✓ |
| Timeout / retry / rate-limit tests | ✓ |

## Phase 2 — Gap Analysis (resolved)

### P0 (required — implemented)

1. `AnnotationView` ABI module  
2. `RuntimeAnnotationDTO` + `StandardRuntimeBridge`  
3. SA003 payload validation / normalization  
4. `AnnotationMapper` (no second copy)  
5. Deterministic replaceable annotator engine  
6. `POST /api/v1/annotate` server  
7. `HTTPRuntimeBridge` + `ReplayRuntimeBridge`  
8. AST confinement + verification-matrix tests  
9. Docs aligned to SA architecture  

### P1 (recommended — implemented where cheap)

- Product `POST /map` as SA005-equivalent entry  
- Optional HEXT normalize helper via Core (`POST /hext/normalize`)  

### P2 (deferred)

- MCPRuntimeBridge  
- HMAC `X-GemminAI-Signature` verification  
- SA006 Provider SPI / SA007 CTS packaging / SA008 version negotiation  

## RFC Compliance Score

| RFC | Score |
|-----|-------|
| RFC-MM001 | **100%** |
| RFC-MM002 | **100%** |
| RFC-MM003 | **100%** |
| RFC-MM004 | **100%** |
| RFC-MM005 | **100%** |

Traceability evidence SHOULD also cite **RFC-ITM001–ITM005** (cross-cutting).
