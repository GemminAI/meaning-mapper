# Meaning Mapper

**Meaning Mapper maps raw observations into standardized HEXT Observation Objects.**  
It is a deterministic, stateless **reference service** for semantic observation normalization in the SensOS Open Standards ecosystem.

| | |
|---|---|
| **Product** | Meaning Mapper |
| **Repository** | [`GemminAI/meaning-mapper`](https://github.com/GemminAI/meaning-mapper) |
| **Python package** | `meaning-mapper` |
| **CLI** | `meaning-mapper` |
| **Docker image** | `gemminai/meaning-mapper` |
| **Canonical HTTP API** | `POST /map` |
| **License** | Apache-2.0 |
| **Version** | 1.0.0 |

> Historical note: the private experimental scaffold formerly named **Semantic Annotator** (`GemminAI/semantic-annotator`) is archived. See [`docs/ARCHIVE_SEMANTIC_ANNOTATOR.md`](docs/ARCHIVE_SEMANTIC_ANNOTATOR.md) and [`docs/MIGRATION.md`](docs/MIGRATION.md).

## What Meaning Mapper is

Meaning Mapper is the **product / container identity** for observation → meaning projection:

```text
Raw observation
      │
      ▼
 Meaning Mapper   ← reference service (this repository)
      │
      ▼
HEXT Observation Object
```

It provides:

- a durable product name and container surface (`gemminai/meaning-mapper`)
- a CLI and HTTP reference service aligned with SensOS Open Standards
- deterministic structural normalization into **HEXT Observation Objects**
- a practical bridge between arbitrary inputs and standardized semantic objects

Internally, normalization is powered by the **Semantic Annotator Core** reference library ([`GemminAI/semantic-annotator-core`](https://github.com/GemminAI/semantic-annotator-core)). Meaning Mapper is the service product layer; Core is the library RI.

## What Meaning Mapper does **not** do

- Storage or knowledge-base writes
- Reasoning, planning, or goal management
- LLM inference or non-deterministic “annotation”
- Runtime orchestration, admission control, or capability tokens
- Enterprise kernel / commercial control-plane behavior

Those concerns belong to other layers (see [Positioning](docs/POSITIONING.md)).

## Ecosystem position

```text
SensOS Open Standards (sensos-docs)
            │
            ▼
semantic-annotator-core     ← Reference Implementation (library)
            │
            ▼
Meaning Mapper              ← Reference service / product container (this repo)
            │
            ▼
nvs-runtime                 ← Reference Runtime (public)
            │
            ▼
nvs-kernel / SensOS         ← Commercial / private enterprise layers
```

| Component | Role | Visibility |
|-----------|------|------------|
| **Meaning Mapper** | Reference service & product identity for observation → HEXT mapping | Public / partner-facing |
| **semantic-annotator-core** | Reference library implementing normalization | Public (Apache-2.0) |
| **nvs-runtime** | Reference runtime for public interoperability contracts | Public |
| **nvs-kernel / SensOS commercial** | Enterprise evaluation, control, and product runtime | Private |

## Quick start

### CLI

```bash
pip install -e ".[dev]"

meaning-mapper examples/sample.json
meaning-mapper notes.md --type markdown
cat examples/sample.json | meaning-mapper -
meaning-mapper --list-adapters
meaning-mapper --version
```

### HTTP reference service

```bash
docker compose up --build -d

curl -s http://localhost:8080/health
curl -s http://localhost:8080/adapters

curl -s http://localhost:8080/map \
  -H 'content-type: application/json' \
  -d '{"document":{"hello":"world"},"source_type":"json"}'
```

`POST /map` returns a **HEXT Observation Object**.

Deprecated compatibility endpoint: `POST /annotate` (same body/response; prefer `/map`).

### Docker

```bash
docker build -f docker/Dockerfile -t gemminai/meaning-mapper:1.0.0 .
docker run --rm -p 8080:8080 gemminai/meaning-mapper:1.0.0
```

## Design principles

- **Deterministic** — same input → same HEXT Observation Object
- **Stateless** — no databases, sessions, or retained process state
- **Schema-first** — emit against the HEXT JSON transport mapping
- **Open-standards aligned** — public contracts over proprietary internals
- **Boundary-clean** — never imports enterprise kernel or commercial runtime control

## Related documentation

| Document | Purpose |
|----------|---------|
| [`docs/POSITIONING.md`](docs/POSITIONING.md) | Product vs library vs runtime vs enterprise |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Service architecture |
| [`docs/BOUNDARIES.md`](docs/BOUNDARIES.md) | What this repo owns and forbids |
| [`docs/NAMING.md`](docs/NAMING.md) | Brand, package, CLI, Docker naming |
| [`docs/MIGRATION.md`](docs/MIGRATION.md) | Migrate from Semantic Annotator names |
| [`docs/ARCHIVE_SEMANTIC_ANNOTATOR.md`](docs/ARCHIVE_SEMANTIC_ANNOTATOR.md) | Historical scaffold archive note |

## Open Standards & HEXT

- SensOS Open Standards: https://sensos.org/Open-Standards
- HEXT JSON transport mapping: https://github.com/HEXT-AI/hxt-spec/blob/main/json/mapping.md

Normative HEXT definitions remain in [HEXT-AI/hxt-spec](https://github.com/HEXT-AI/hxt-spec).  
This repository does not redefine the specification or expose proprietary runtime technology.

## Naming family

| Brand | Use |
|-------|-----|
| **Meaning Mapper** | Primary product name (preferred) |
| Meaning Projector | Alternate architectural metaphor (docs only) |
| Meaning Compiler | Alternate structural metaphor (docs only) |

Do not use “Semantic Annotator” in new product-facing materials except for migration / compatibility notes.

## License

Apache License 2.0 — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
