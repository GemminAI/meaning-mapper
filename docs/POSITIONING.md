# Architecture positioning

**Meaning Mapper** is the canonical product name for the observation → meaning projection reference service.

## Layer map

```text
SensOS Open Standards (sensos-docs)
        │ constrains
        ▼
semantic-annotator-core          ← Reference Implementation (library)
        │ consumed by
        ▼
Meaning Mapper                   ← Reference service / product / container (this repo)
        │ feeds (optionally)
        ▼
nvs-runtime                      ← Reference Runtime (public)
        │ enterprise product path
        ▼
nvs-kernel / SensOS commercial   ← Private enterprise layers
```

## Clear statements

| Assertion | Status |
|-----------|--------|
| Meaning Mapper is a **reference service / product layer** | Yes |
| semantic-annotator-core is the **reference library** | Yes |
| nvs-runtime is the **reference runtime** | Yes |
| nvs-kernel / SensOS commercial layers remain **private** | Yes |
| Meaning Mapper exposes kernel logic, DAK, or Execution Algebra | **No** |
| Meaning Mapper performs LLM inference | **No** |

## How Meaning Mapper differs from nearby components

### vs semantic-annotator-core

| | Meaning Mapper | semantic-annotator-core |
|--|----------------|-------------------------|
| Role | Product + container + service surface | Library RI |
| Brand | Meaning Mapper | Historical library name (kept for package stability) |
| CLI | `meaning-mapper` | `semantic-annotator` |
| Docker | `gemminai/meaning-mapper` | `gemminai/semantic-annotator-core` |
| Canonical HTTP | `POST /map` | `POST /annotate` |

Integrators building applications should prefer **Meaning Mapper**.  
Library authors embedding normalization may depend on **semantic-annotator-core** directly.

### vs nvs-runtime

| | Meaning Mapper | nvs-runtime |
|--|----------------|-------------|
| Concern | Structural meaning projection of observations | Runtime hosting of public observation / control contracts |
| Output focus | HEXT Observation Objects | Runtime behavior under public RFCs |
| Scope | Stateless transform service | Runtime lifecycle and protocol surfaces |

### vs enterprise / proprietary services

Enterprise SensOS services (including any internal meaning-attachment pipelines) may:

- consume Meaning Mapper or Core outputs
- add proprietary enrichment, tenancy, auth, or control

They **must not** be confused with this open reference service. Meaning Mapper intentionally excludes proprietary runtime technology.

## Product metaphors (non-normative)

- **Meaning Mapper** — primary brand: maps observations into a meaning-space representation
- **Meaning Projector** — projects structure into a standardized semantic coordinate system
- **Meaning Compiler** — compiles heterogeneous inputs into a canonical object form

Only **Meaning Mapper** is normative for repository, package, CLI, and Docker identity.
