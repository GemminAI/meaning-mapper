# Repository boundaries

## Owns

- Meaning Mapper product identity (brand, README, package, CLI, Docker)
- Reference HTTP service surface (`/map`, `/health`, `/adapters`)
- Migration and archive documentation for the Semantic Annotator rename
- Compatibility shims that preserve integrator continuity without leaking proprietary tech

## Does not own

| Concern | Owner |
|---------|-------|
| Normalization algorithms / adapters | [`semantic-annotator-core`](https://github.com/GemminAI/semantic-annotator-core) |
| HEXT normative schema / XSD | [HEXT-AI/hxt-spec](https://github.com/HEXT-AI/hxt-spec) |
| Open Standards RFCs & conformance | [`sensos-docs`](https://github.com/GemminAI/sensos-docs) / [sensos.org](https://sensos.org/Open-Standards) |
| Reference runtime protocols | [`nvs-runtime`](https://github.com/GemminAI/nvs-runtime) |
| Enterprise evaluation / control | `nvs-kernel` / SensOS commercial (private) |
| Knowledge persistence | HEKB (downstream) |

## Forbidden in this repository

- Kernel logic, DAK internals, Execution Algebra
- Enterprise runtime admission, CBAC private mechanics, budget/control orchestration details
- LLM provider SDKs or non-deterministic enrichment pipelines
- Secrets, billing, multi-tenant auth products

## Security posture

Meaning Mapper is intentionally secret-light: no API keys or database passwords are required for the reference transform path.
