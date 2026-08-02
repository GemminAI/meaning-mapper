# Meaning Mapper

**SensOS Open Standards Reference Service** for semantic annotation
([RFC-SA001](docs/RFC_COMPLIANCE.md)–[RFC-SA005](docs/RFC_COMPLIANCE.md)).

Meaning Mapper maps **Measured Observations** into versioned, frozen
**AnnotationView** snapshots (SA002) with SA003 payloads — deterministically,
without mutating source measurements, and without commercial runtime technology.

| | |
|---|---|
| **Product** | Meaning Mapper |
| **Repository** | [`GemminAI/meaning-mapper`](https://github.com/GemminAI/meaning-mapper) |
| **Python package** | `meaning-mapper` |
| **CLI** | `meaning-mapper` |
| **Docker image** | `gemminai/meaning-mapper` |
| **Canonical product API** | `POST /map` |
| **RFC transport API** | `POST /api/v1/annotate` |
| **Library RI** | [`semantic-annotator-core`](https://github.com/GemminAI/semantic-annotator-core) |
| **License** | Apache-2.0 |
| **Version** | 1.0.0 |
| **RFC compliance** | SA001–SA005 **100%** — see [`docs/RFC_COMPLIANCE.md`](docs/RFC_COMPLIANCE.md) |

## What it does

- Accepts measured observational data (SA005 request)
- Produces descriptive SA003-aligned annotations via a **replaceable** engine
- Lifts mutable runtime DTOs across the **sole** Runtime Bridge copy boundary (SA004)
- Exposes frozen `AnnotationView` / `AnnotatedObservation` to domain consumers (SA002)
- Remains usable when annotation fails (Principle 5 → empty view)

## What it does **not** do

- LLM inference or proprietary model orchestration
- Mutate MeasuredObservation values
- Import NVS-Kernel, HEKB, or SensOS commercial internals
- Persist annotations or own storage

## Ecosystem

```text
HEXT
  → semantic-annotator-core   (Reference Library)
  → Meaning Mapper            (Reference Service — this repo)
  → nvs-runtime               (Reference Runtime)
  → SensOS / NVS-Kernel       (Commercial)
```

## Quick start

### HTTP (RFC-SA005)

```bash
docker compose up --build -d

curl -s http://localhost:8080/health

curl -s http://localhost:8080/api/v1/annotate \
  -H 'content-type: application/json' \
  -d @examples/sa005_request.json

# Product canonical alias (same contract):
curl -s http://localhost:8080/map \
  -H 'content-type: application/json' \
  -d @examples/sa005_request.json
```

Deprecated: `POST /annotate` (same body; prefer `/map` or `/api/v1/annotate`).

### CLI

```bash
pip install -e ".[dev]"

meaning-mapper annotate examples/sa005_request.json
meaning-mapper examples/sample.json   # bare observational JSON
meaning-mapper hext examples/sample.json   # optional Core HEXT normalize
```

### SDK

```python
from meaning_mapper import map_annotation
from meaning_mapper.engine import DeterministicAnnotatorEngine
from meaning_mapper.runtime_bridge import StandardRuntimeBridge

wire = DeterministicAnnotatorEngine().annotate(
    observation_id="obs_1",
    prompt_id="prompt_stability_analysis_v1",
    raw_observational_data={"acceleration": [0.01, -0.05, 9.81]},
)
view = StandardRuntimeBridge().bridge_annotation(wire)
annotated = map_annotation("prompt_stability_analysis_v1", view, observation_id="obs_1")
```

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

```text
MeasuredObservation
  → AnnotatorEngine (replaceable)
  → RuntimeAnnotationDTO          # confined to runtime_bridge.py
  → Runtime Bridge (single copy)
  ======== SA-002 ABI BOUNDARY ========
  → AnnotationView (frozen)
  → Annotation Mapper (no second copy)
  → AnnotatedObservation
```

## Documentation

| Doc | Purpose |
|-----|---------|
| [`docs/RFC_COMPLIANCE.md`](docs/RFC_COMPLIANCE.md) | Compliance matrix & scores |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Layer diagram |
| [`docs/REFACTORING_REPORT.md`](docs/REFACTORING_REPORT.md) | Files changed |
| [`docs/POSITIONING.md`](docs/POSITIONING.md) | Product vs library vs runtime |
| [`docs/MIGRATION.md`](docs/MIGRATION.md) | Legacy name migration |
| [`docs/BOUNDARIES.md`](docs/BOUNDARIES.md) | Ownership / forbidden imports |

## Tests

```bash
pytest
ruff check src tests
```

Verification matrices cover RFC-SA002–SA005 (DTO confinement, ignore-unknowns,
density clamp, defensive isolation, timeout/retry/429 client behavior).

## License

Apache License 2.0 — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
