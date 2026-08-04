# Changelog

## 2.1.0 — 2026-08-04

### Reverted: Categorical Lift is an independent component again

Hours after the 2.0.0 rebuild integrated Categorical Lift into Meaning
Mapper, that decision was reverted: SensOS's product architecture is tiered
(OSS: `semantic-annotator-core` + Meaning Mapper + MSR, fully usable with no
cloud dependency; Pro: Categorical Lift Engine; Enterprise: HEKB Cloud), and
Categorical Lift — trajectory interpretation, concept discovery, knowledge
crystallization, HEKB integration — is Pro-tier knowledge generation, not
OSS-tier measurement. The software boundary now matches the product
boundary. See `docs/RFC_COMPLIANCE.md` for the full rationale.

- Renamed the pipeline's stage 6 from Categorical Lift to **Semantic
  Projection** (`src/meaning_mapper/projection/semantic_projection.py`,
  formerly `lift/categorical_lift.py`): a fixed, non-extensible geometric
  projection (`theta = frame.basis @ raw_features`), with no
  `typing.Protocol` seam and no framing toward functors, natural
  transformations, pullbacks, pushouts, or commutative diagrams — that
  extensibility now belongs entirely to the independent Categorical Lift
  Engine (CLE), a separate repository.
- `map_observation` no longer takes a pluggable `lift` parameter.
- `QuarantineStage.CATEGORICAL_LIFT` renamed to
  `QuarantineStage.SEMANTIC_PROJECTION`.
- `docs/BOUNDARIES.md` rewritten: CLE has its own Input/Output/Owns/Must-not
  section and an ecosystem-table row; MM's Must-not list now explicitly
  names Concept generation, Category generation, Knowledge Crystallization,
  Homotopy Analysis, and HEKB commits.
- 71 tests, 100% line + branch coverage maintained, ruff clean, mypy strict
  clean.

## 2.0.0 — 2026-08-04

### Rebuilt as the geometric Meaning Measurement engine

Replaces the RFC-SA-era `AnnotationView` ABI service with the pipeline
RFC-MSR01 actually requires upstream of `meaning-space-runtime`: HEXT
Observation in, `MeaningMeasurement` (`theta`, `sigma`) out. See
`docs/RFC_COMPLIANCE.md` for the RFC-MM001–MM005 documentation sync gap this
change surfaces.

- Eight-stage deterministic pipeline: Observation Validation, Metric Tensor
  Estimation, Local Frame Resolution, Density Estimation, Covariance
  Estimation, Categorical Lift (internal), Topological Consistency Check,
  MeaningMeasurement Generation.
- `MeaningMeasurement`, structurally compatible with `msr.abi.MeaningMeasurement`
  / `msr.adapters.mapper.measurement_from_payload` — no shared import with
  `msr` or `semantic-annotator-core`; every crossing is a structural port.
- `CategoricalLift` is a `typing.Protocol` extension seam (functor / natural
  transformation / pullback / pushout / commutative diagram, later) around a
  deterministic linear default. No independent `cle` module or repository.
- Never raises for a rejected observation: `map_observation` returns a
  `MeasurementResult` (`.measurement` or `.quarantine`, never both).
- 72 tests, 100% line + branch coverage (enforced via `fail_under = 100`),
  ruff clean, mypy strict clean.
- Dropped the FastAPI/uvicorn/httpx HTTP service, CLI, and Docker image (not
  part of the requested architecture); the pre-2026-08-04 `AnnotationView`
  service is preserved under `legacy/rfc-sa-annotation-service/`.

### Compliance

| RFC | Status |
|-----|--------|
| RFC-MSR01 | Structural port satisfied (`MeaningMeasurement` shape) |
| RFC-MM001–MM005 (published text) | Sync gap — see `docs/RFC_COMPLIANCE.md` |
| RFC-SA001–SA005 | Historic; superseded; implemented by the legacy tree only |

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
