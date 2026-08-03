# Architecture

Meaning Mapper is the **SensOS Open Standards Reference Service** for the
**RFC-MM001–MM005** Meaning Mapper product series (legacy RFC-SA001–SA005 are
Superseded).

It is **model-independent**, deterministic, and built on top of
[`semantic-annotator-core`](https://github.com/GemminAI/semantic-annotator-core)
(library RI) for optional structural HEXT metrics. It contains no NVS-Kernel,
HEKB, SensOS commercial internals, or proprietary runtime orchestration.

## Final architecture diagram

```text
       [ Reality ]
            │
            ▼
 [ MeasuredObservation ]  (immutable measurement)
            │
            ├──────────────────────────────┐
            │                              ▼
            │                 [ AnnotatorEngine ]  (replaceable; default deterministic)
            │                              │
            │                              ▼
            │                 [ RuntimeAnnotationDTO ]  ← confined to runtime_bridge.py
            │                              │
            │                              ▼
            │                 [ Runtime Bridge ]  ← sole defensive copy (SA004)
            │                              │
            │                 ========== SA-002 ABI BOUNDARY ==========
            │                              │
            │                              ▼
            │                      [ AnnotationView ]  (frozen)
            │                              │
            │                              ▼
            │                   [ Annotation Mapper ]  (no second copy)
            │                              │
            ▼                              ▼
         [ AnnotatedObservation ]
            │
            ▼
   (downstream: ObservationDescriptor / EXP-5000 / nvs-runtime — out of scope)
```

## Ecosystem position

```text
HEXT Spec / SensOS Open Standards
        │
        ▼
semantic-annotator-core     ← Reference Library
        │
        ▼
Meaning Mapper              ← Reference Service (this repo, RFC-SA001–SA005)
        │
        ▼
nvs-runtime                 ← Reference Runtime
        │
        ▼
SensOS / NVS-Kernel         ← Commercial (private)
```

## Package map

| Path | RFC | Responsibility |
|------|-----|----------------|
| `abi/` | SA002 | `AnnotationView`, `AnnotatedObservation` |
| `payload/` | SA003 | Payload vocabulary, density, normalize |
| `mapper/` | SA001/002 | `map_annotation` (no second copy) |
| `runtime_bridge.py` | SA004/005 | DTO confinement, Standard/HTTP/Replay bridges |
| `engine/` | SA001 | Replaceable descriptive annotator |
| `service.py` | SA005 | HTTP reference service |
| `cli.py` | — | CLI for annotate + optional HEXT |

## HTTP surface

| Method | Path | Status |
|--------|------|--------|
| `POST` | `/api/v1/annotate` | **RFC-SA005 normative** |
| `POST` | `/map` | **Product canonical** (same SA005 contract) |
| `POST` | `/annotate` | Deprecated compatibility alias |
| `GET` | `/health` | Liveness |
| `POST` | `/hext/normalize` | Optional Core HEXT helper (not SA005) |

## Principles (RFC-SA001)

1. Descriptive — no hidden-state inference  
2. External — never mutate MeasuredObservation  
3. Reproducible — deterministic default engine  
4. Replaceable — `AnnotatorEngine` protocol  
5. Optional — empty `AnnotationView` on transport/schema failure  
