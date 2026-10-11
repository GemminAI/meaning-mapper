# Changelog

## Unreleased

### Temporal context and a time-aware discontinuity guard (additive)

- `MeaningMeasurement.temporal_context`: the HEXT Observation's declared
  `semantic.metadata.time_frame` is carried through unchanged and never measured
  (excluded from the hashed features; `theta`/`sigma`/`density`/`measurement_id`
  unaffected; integrity-covered by `provenance_hash` only when present).
  Malformed values are quarantined at validation.
- `process()` / `map_observation()`: optional `previous_timestamp_ns` and
  `discontinuity_rate_max` make the Non-Discontinuity Guard judge the jump as a rate
  over the elapsed time. No default bound; omitting either keeps RFC-MM004v2 SS4.
- `check_discontinuity_over_time()` (pure function) behind it.
- Tests: 146 -> 165, still 100% line + branch coverage. See `docs/RFC_ALIGNMENT.md` SS8.

## 2.3.0 — 2026-08-12

### `meaning_mapper.cle`: HTTP adapter to the independent CLE service

A new subpackage — `client.py`, `models.py`, `errors.py`, `grounding.py` —
adds an HTTP-only client to Categorical Lift Engine (CLE)'s API
(`health`, `ground`, `lift`, `pullback`, `recover`, `compress`), verified
against CLE's own live `/openapi.json`, not assumed. This does not revise
`docs/BOUNDARIES.md`'s "CLE is independent, do not embed its algorithms
here" decision (2.1.0, below) — no CLE algorithm is reimplemented; every
adapter method builds a request, sends it, and parses the response.

- **`grounding.py`**: `ground_observation()` bridges a real HEXT
  Observation to CLE's `/ground`, reusing the existing, unmodified
  `validate_observation()` (a malformed Observation quarantines exactly as
  it already does for measurement — no new failure mode invented).
  `text`/`metadata`/`timestamp_ns`/`provenance`/`state_hash`/
  `observation_id` are carried through unmodified; nothing is inferred
  that the Observation does not actually carry. `goal` is a required,
  explicit, caller-supplied parameter — HEXT Observations have no `goal`
  field in their real wire format, and none is derived from `text` or
  fabricated. `GroundedObservation` (the result) ties CLE's response back
  to the source Observation's own identity/provenance and is a distinct
  type from `MeaningMeasurement`, never merged with it.
- **`ConceptInput.from_measurement()`**: the explicit, named connection
  between a real `MeaningMeasurement.theta` and CLE's `/lift`. Reads
  `.theta` only — `.sigma`/`.density`/`.provenance` are not carried into
  CLE, since `ConceptInput` has no fields for them.
- Three typed failure modes throughout the adapter — `CLEUnreachableError`
  (network/timeout), `CLEHTTPError` (4xx/5xx, carries `status_code`), and
  `CLESchemaError` (a 200 response missing a required field) — never one
  bare exception, and never silently reinterpreted as a `QuarantineReason`
  (quarantine stays reserved for the Observation itself being unusable).
- The existing measurement pipeline (`pipeline.py`, `types.py`, every
  stage module) is unchanged. `legacy/rfc-sa-annotation-service/` is
  unchanged and unused.
- New dependency: `httpx>=0.27` (this repository's only other dependency
  remains `numpy`; no pydantic introduced — `cle/models.py` uses the same
  `@dataclass(frozen=True, slots=True)` convention as the rest of this
  repository).
- 48 new tests (146 total, was 98), 100% line + branch coverage maintained,
  ruff clean, mypy --strict clean. Includes live integration tests against
  a real running CLE service for all 6 endpoints (not mocks alone), and a
  live end-to-end test of the real, unmodified measurement pipeline's
  output flowing into a real CLE `/lift` call.

## 2.2.0 — 2026-08-04

### RFC-MM001–005 v2 conformance pass

RFC-MM001v2–RFC-MM005v2 ("Post-Implementation Realignment") were adopted as
the canonical spec for this repository, superseding the v1 `AnnotationView`
ABI text. This release closes every gap between the 2.1.0 implementation
and the v2 RFCs that had a well-specified, non-contradictory resolution; two
items (`betti_numbers`, internal state for the discontinuity guard) were
intentionally left unimplemented because doing so would have violated this
repository's own boundary rules. See `docs/RFC_ALIGNMENT.md` for the full
audit matrix and the reasoning behind every deviation below — nothing here
is hidden.

- **Immutability fix (RFC-MM002 SS4.2)**: `MetricTensor.matrix`,
  `LocalFrame.basis`/`.metric_tensor`, and `Covariance.matrix` were
  `numpy.ndarray` fields on `frozen=True` dataclasses — mutable in place
  despite the frozen wrapper. All three now store frozen `Matrix` tuples,
  deep-copied at construction regardless of input type; a `.array` property
  reconstructs the mutable view on demand for internal linear algebra.
- **`LocalFrame`** gained `frame_id`, `metric_tensor`, and derived
  `ambient_dim`/`semantic_dim` properties (RFC-MM002 SS2.2).
- **`MeaningMeasurement`** gained `density` (RFC-MM003's entropy-based
  `D_s ∈ [0, 1]`, a new, separate quantity from the pre-existing internal
  evidence-density scalar), `measurement_id` (deterministic UUID5, never
  UUID4 — RFC-MM005 SS2.1 requires bit-identical reproducibility), and
  `provenance_hash` (SHA-256 over the measurement's own defining fields).
  `sigma`/`frame_id`/`provenance` are kept as-is rather than renamed to the
  RFC's `covariance`, since MSR's real, already-verified wire contract uses
  the former names.
- **Covariance Estimation** reworked to RFC-MM003 SS4's canonical
  `Σ = σ²_input · (B·Bᵀ)` form (`σ²_input := 1/density.value`) — verified
  bit-for-bit equivalent to the prior `inverse(g)/density` formula, since a
  whitening frame's `B·Bᵀ == g⁻¹` exactly. `estimate_covariance()` now takes
  the `LocalFrame` instead of the `MetricTensor` directly.
- **Non-Discontinuity Guard** (RFC-MM004 SS4) added as a new, stateless
  `check_discontinuity()` function. Meaning Mapper never remembers a prior
  θ; callers pass `previous_theta` explicitly to `map_observation()` /
  `MeaningMapperPipeline.process()` on each call that wants the guard
  evaluated. `THETA_DISCONTINUITY_MAX` is a documented experimental default
  (RFC gives no numeric value).
- **`MeaningMapperPipeline`** (RFC-MM004 SS2) added as the RFC-named entry
  point; `map_observation()` is now a thin delegate to it.
  `MeasurementResult.is_valid` added alongside the pre-existing
  `is_quarantined`.
- `ValidatedObservation.feature_dim` added (RFC-MM002 SS2.1).
- `betti_numbers` (RFC-MM001/002) intentionally **not** implemented:
  `docs/BOUNDARIES.md` forbids Meaning Mapper from performing homotopy
  analysis; treated as an RFC drafting inconsistency, flagged for a
  separate RFC-authoring pass.
- 98 tests (was 71), 100% line + branch coverage maintained, ruff clean,
  mypy --strict clean.

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
