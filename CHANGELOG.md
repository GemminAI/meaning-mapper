# Changelog

## 1.0.0 — 2026-08-02

### Added — RFC-SA001–SA005 canonical implementation

- `AnnotationView` / `AnnotatedObservation` ABI (SA002)
- SA003 payload schema, density clamp, ignore-unknowns
- `StandardRuntimeBridge`, `HTTPRuntimeBridge`, `ReplayRuntimeBridge` (SA004/005)
- Deterministic replaceable `AnnotatorEngine` (model-independent)
- `POST /api/v1/annotate` (RFC-SA005) and product `POST /map`
- Deprecated `POST /annotate` compatibility alias
- Optional `POST /hext/normalize` via semantic-annotator-core
- AST confinement + full verification-matrix tests
- `docs/RFC_COMPLIANCE.md`, architecture & refactoring reports

### Compliance

| RFC | Score |
|-----|-------|
| SA001 | 100% |
| SA002 | 100% |
| SA003 | 100% |
| SA004 | 100% |
| SA005 | 100% |

### Notes

- Does not rename `semantic-annotator-core`
- No LLM, NVS-Kernel, HEKB, or commercial orchestration
