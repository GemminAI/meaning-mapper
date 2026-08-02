# Architecture

Meaning Mapper is a thin **reference service** over the Semantic Annotator Core normalization engine.

## Pipeline

```text
Input (file / stdin / HTTP document)
  → Adapter selection
  → Normalizer
  → Metadata extraction
  → HEXT Observation Object builder
  → Validator
  → JSON output
```

All stages are deterministic with respect to process state. No database. No LLM. No network required for the transform itself.

## Repository layout

| Path | Responsibility |
|------|----------------|
| `src/meaning_mapper/` | Product SDK entry, CLI, HTTP service |
| `docker/` | Container image for the reference service |
| `docs/` | Product positioning, migration, boundaries |
| `examples/` | Sample inputs |
| `tests/` | Service-surface tests |

Normalization algorithms live in [`semantic-annotator-core`](https://github.com/GemminAI/semantic-annotator-core). This repository owns product identity, packaging, and the public service contract.

## HTTP surface

| Method | Path | Status |
|--------|------|--------|
| `GET` | `/health` | Active |
| `GET` | `/adapters` | Active |
| `POST` | `/map` | **Canonical** |
| `POST` | `/annotate` | Deprecated compatibility alias |

## Dependency direction

```text
HEXT Specification
        ↓
semantic-annotator-core (library RI)
        ↓
Meaning Mapper (this service)
        ↓
Consumers (partners, nvs-runtime, applications)
```

Meaning Mapper must never import SensOS commercial modules, nvs-kernel, HEKB storage clients, or proprietary control-plane code.
