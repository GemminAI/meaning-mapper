# Migration guide

This guide helps integrators move from historical **Semantic Annotator** names to **Meaning Mapper**.

## Summary

| Old | New |
|-----|-----|
| Private scaffold `GemminAI/semantic-annotator` | **Archived** — use `GemminAI/meaning-mapper` |
| Product brand “Semantic Annotator” | **Meaning Mapper** |
| CLI `semantic-annotator` (product use) | CLI `meaning-mapper` |
| Docker `semantic-annotator` / `gemminai/semantic-annotator-core` (product use) | Docker `gemminai/meaning-mapper` |
| Package `semantic-annotator` (product install) | Package `meaning-mapper` |
| HTTP `POST /annotate` | HTTP `POST /map` |
| Library embedding of Core | Still `semantic-annotator` / `GemminAI/semantic-annotator-core` |

## 1. Repository

| Action | Detail |
|--------|--------|
| Stop | Opening PRs against `GemminAI/semantic-annotator` |
| Start | Develop against `GemminAI/meaning-mapper` |
| History | Scaffold commits remain readable in the archived repository |

Archive rationale: [`ARCHIVE_SEMANTIC_ANNOTATOR.md`](ARCHIVE_SEMANTIC_ANNOTATOR.md).

## 2. CLI

Old (scaffold / library product confusion):

```bash
semantic-annotator examples/sample.json
```

New:

```bash
meaning-mapper examples/sample.json
```

Compatibility: installing `meaning-mapper` currently provides a deprecated `semantic-annotator` console script that emits `DeprecationWarning` and delegates to Meaning Mapper. Remove reliance on it before **2.0**.

## 3. Docker

Old (library image used as a product):

```bash
docker run --rm -p 8080:8080 gemminai/semantic-annotator-core:1.0.0
```

New:

```bash
docker run --rm -p 8080:8080 gemminai/meaning-mapper:1.0.0
# or
docker compose up --build
```

Compose service rename: `semantic-annotator` → `meaning-mapper`.

## 4. Package / Python

Product install:

```bash
pip install meaning-mapper   # when published
# or from source
pip install -e ".[dev]"
```

```python
from meaning_mapper import map_observation

obj = map_observation({"event": "boot", "device": "sensor-1"})
```

Library-only embedders may continue:

```python
from semantic_annotator import annotate
```

## 5. HTTP API

| | Old | New |
|--|-----|-----|
| Path | `POST /annotate` | `POST /map` |
| Body | `{ "document": ..., "source_type": ... }` | unchanged |
| Response | HEXT Observation Object | unchanged |
| Health `service` field | `semantic-annotator-core` | `meaning-mapper` |

`POST /annotate` remains temporarily as a deprecated alias on Meaning Mapper.

## 6. Compatibility shims (current major)

| Shim | Behavior | Removal target |
|------|----------|----------------|
| CLI entry `semantic-annotator` | Warn + delegate | Meaning Mapper 2.0 |
| `POST /annotate` | Identical to `/map` | Meaning Mapper 2.0 |
| Core package name `semantic-annotator` | Unchanged (library) | Separate library rename, if ever |

## 7. What does **not** migrate here

- Proprietary SensOS commercial annotator services
- Enterprise kernel / nvs-kernel APIs
- Non-deterministic LLM enrichment pipelines

Those are out of scope for Meaning Mapper.
