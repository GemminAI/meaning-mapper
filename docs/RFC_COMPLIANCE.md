# RFC-SA001–SA005 Compliance Matrix

**Product:** Meaning Mapper v1.0  
**Authority:** RFC-SA001 … RFC-SA005 (canonical)  
**Date:** 2026-08-02

## Phase 1 — Architecture Compliance Report (pre → post)

| RFC | Pre-impl | Post-impl | Status |
|-----|----------|-----------|--------|
| RFC-SA001 | ~15% | **100%** | Principles + layer map implemented |
| RFC-SA002 | ~0% | **100%** | `AnnotationView` ABI + confinement tests |
| RFC-SA003 | ~0% | **100%** | Payload schema + density clamp + ignore unknowns |
| RFC-SA004 | ~0% | **100%** | `runtime_bridge.py` single copy boundary |
| RFC-SA005 | ~10% | **100%** | `POST /api/v1/annotate` + resilient client bridge |

### RFC-SA001 — Semantic Annotation Architecture

| Requirement | Status |
|-------------|--------|
| P1 Descriptive (no hidden-state inference in annotations) | ✓ Deterministic descriptive engine |
| P2 External (does not mutate MeasuredObservation) | ✓ Observation passed by value; never rewritten |
| P3 Reproducible | ✓ Deterministic annotator; same input → same view |
| P4 Replaceable provider | ✓ `AnnotatorEngine` protocol |
| P5 Optional (empty view on failure) | ✓ Neutral `AnnotationView()` fallback |
| Layer: Annotator → Bridge → View → Mapper | ✓ |
| No transport / storage / kernel in architecture core | ✓ |

### RFC-SA002 — Annotation View ABI

| Requirement | Status |
|-------------|--------|
| Frozen `AnnotationView` fields | ✓ |
| `RuntimeAnnotationDTO` confined to `runtime_bridge.py` | ✓ AST test |
| Domain modules ban `httpx`/`requests` | ✓ AST test |
| Public `__all__` domain-neutral only | ✓ |
| Ignore unknowns | ✓ |
| Single defensive copy at bridge | ✓ |
| `RuntimeBridge` protocol | ✓ |

### RFC-SA003 — Annotation Payload Schema

| Requirement | Status |
|-------------|--------|
| `schema_id` = `urn:gemminai:schema:sa003:1.0` | ✓ |
| `payload_class` ∈ categorical\|spatial\|evaluative\|hybrid | ✓ |
| `generator_signature` required | ✓ |
| Categorical / spatial / evaluative vocab | ✓ |
| `semantic_density` clamp `[0,1]` | ✓ |
| Ignore unknowns / nullable defaults | ✓ |

### RFC-SA004 — Runtime Bridge

| Requirement | Status |
|-------------|--------|
| `bridge_annotation` single copy | ✓ |
| Tuple freeze for coordinates | ✓ |
| Dict defensive copy (deep when nested) | ✓ |
| schema_id validation / drop | ✓ |
| Type coercion + safe defaults | ✓ |
| `StandardRuntimeBridge` / `ReplayRuntimeBridge` | ✓ |
| Isolation / ignore-extra / density tests | ✓ |

### RFC-SA005 — Semantic Annotator API

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
| RFC-SA001 | **100%** |
| RFC-SA002 | **100%** |
| RFC-SA003 | **100%** |
| RFC-SA004 | **100%** |
| RFC-SA005 | **100%** |
