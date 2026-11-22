# RFC-MM001–005 v2 Alignment

Tracks this repository's conformance to RFC-MM001v2–RFC-MM005v2 (the
"Post-Implementation Realignment" specs, 2026-08-04), and documents every
intentional deviation, experimental assumption, and RFC ambiguity found
while implementing them. Nothing below is hidden or silently resolved.

## 0. Two items intentionally out of scope (resolved 2026-08-04)

**`betti_numbers` (RFC-MM001v2 Stage 7 diagram, RFC-MM002v2 SS2.3) is not
implemented.** Producing Betti numbers requires homotopy/homology analysis,
and [`docs/BOUNDARIES.md`](BOUNDARIES.md) explicitly lists "Perform Homotopy
Analysis" under Meaning Mapper's **Must-not** list — a boundary rule that
predates and is not superseded by the v2 realignment. This is treated as an
RFC drafting inconsistency carried over from the architecture diagram, not
as a requirement to implement. `MeaningMeasurement` has no `betti_numbers`
field. Homotopy/homology analysis belongs to the Categorical Lift Engine
(CLE), per the existing boundary table. Flagged for a separate RFC-authoring
pass; not fixed here.

**The Non-Discontinuity Guard (RFC-MM004v2 SS4) does not give Meaning Mapper
any internal state.** `‖θₜ − θₜ₋₁‖ > Δmax` needs the previous observation's
θ, which conflicts with RFC-MM001's "Pure Library & Zero Side Effects" and
`docs/ARCHITECTURE.md`'s "no stage... holds state across observations."
Resolution: `previous_theta` is an optional parameter on
`MeaningMapperPipeline.process()` / `map_observation()`, supplied explicitly
by the caller (e.g. MSR, which already assembles trajectories) on every call
it wants the guard evaluated for. Meaning Mapper never retains it. Without
`previous_theta`, the guard is not evaluated (RFC-MM004 gives no other
prescribed behavior for its absence). See
[`topology/topological_consistency.py`](../src/meaning_mapper/topology/topological_consistency.py)
`check_discontinuity`.

## 1. `HEXTObservation` shape (RFC-MM002v2 SS2.1)

RFC-MM002v2 describes `HEXTObservation` as a flat
`{observation_id, timestamp_ns, features, feature_dim, sensor_hash}` record.
The real upstream HEXT wire format produced by `semantic-annotator-core` is
nested JSON (`object`/`evidence`/`final_seal`/`semantic`/`provenance`
sections) — `types.HEXTObservation` (a `Mapping[str, Any]`) and
`validate_observation()` reflect that real shape, not the RFC's flat one.
Renaming `ValidatedObservation`'s fields (`text`, `metadata`, `content_hash`)
to match the RFC would break real HEXT ingestion for no behavioral gain, so
they were kept. `feature_dim` (RFC-MM002v2's one field this repo was
genuinely missing and can derive losslessly) was added as a property on
`ValidatedObservation`. `content_hash` is the closest analogue to the RFC's
`sensor_hash` — same role (integrity hash carried from upstream), different
name, not unified, since they are documented from different source fields
(`final_seal.state_hash` vs. an unspecified RFC source).

## 2. `MeaningMeasurement` naming (RFC-MM002v2 SS2.3)

- **`sigma` vs. `covariance`**: RFC-MM002v2 names the uncertainty field
  `covariance`. This repository keeps `sigma`, because `msr.abi.MeaningMeasurement`
  — the real, already-built, RFC-MSR01-verified downstream consumer — uses
  `sigma`, and this repository does not control that contract
  ([`docs/BOUNDARIES.md`](BOUNDARIES.md) "Crossings are structural, not
  shared imports"). Renaming would silently break real MSR interoperability
  to satisfy a naming preference. Same reasoning for keeping `frame_id`
  (present in the real MSR contract, absent from RFC-MM002v2 SS2.3).
- **`provenance` vs. `provenance_hash`**: these are two different concepts
  that happen to share a word. `provenance: tuple[str, ...]` (pre-existing)
  is contributor/agent lineage (e.g. `"software:semantic-annotator@1.0.0"`).
  `provenance_hash: str` (new, RFC-MM002v2 SS2.3) is a SHA-256 integrity hash
  over the measurement's own defining fields (`observation_id`, `frame_id`,
  `theta`, `sigma`, `timestamp_ns`) — RFC-MM002v2 calls for a hash "of the
  input, frame, and computation parameters" without enumerating them; those
  fields are exactly what determines `theta`/`sigma`, so hashing the
  measurement's own output is equivalent and needs no separate parameter
  bag. Both fields are kept, distinctly, on `MeaningMeasurement`.
- **`measurement_id`**: added as UUID5 (`uuid.uuid5(uuid.NAMESPACE_URL, ...)`),
  not UUID4. RFC-MM005v2 SS2.1 requires bit-identical reproducibility across
  processes; UUID4 is OS-entropy-seeded and would violate that on its own,
  so a pure hash-based UUID was used instead. Derived from
  `observation_id:frame_id:timestamp_ns` — never caller-supplied, so it
  cannot drift from what it identifies.
- **`ambient_dim` / `semantic_dim`** (RFC-MM002v2 SS2.2, on `LocalFrame`):
  implemented as derived properties, not stored fields, since this
  implementation's projection is a full-rank whitening map with no
  dimensionality reduction — `ambient_dim == semantic_dim` always, by
  construction, for every `LocalFrame` this repository can produce. True
  `m < d` dimensionality reduction is not implemented.

## 3. RFC-MM003v2 mathematics

### 3.1 `D_s = clamp(c * (1 - H/H_max), 0, 1)` — the `c` term

RFC-MM003v2 SS3 does not say where the confidence scalar `c` comes from, and
the v2 pipeline has no external confidence/annotation input feeding Density
Estimation (unlike the legacy RFC-SA003 payload schema, which read it from
an annotator-supplied field — see `legacy/rfc-sa-annotation-service/`).
`c = 1.0` (`SEMANTIC_DENSITY_CONFIDENCE` in
[`density/density_estimation.py`](../src/meaning_mapper/density/density_estimation.py))
is the documented default for "no confidence source exists." An all-zero or
single-element feature vector has no distribution to form `p_i` from
(`0/0`); `D_s` is defined as `0.0` in that case, consistent with Local Frame
Resolution's existing "nothing local yet" bootstrap for the same input.

### 3.2 Two different "density" quantities share a name

`Density` / `estimate_density()` (pre-existing, unchanged behavior) is an
internal evidence-mass scalar clamped to `[DENSITY_FLOOR, DENSITY_CEILING]
= [1e-3, 1e3]`, used only as Covariance Estimation's `1/density` scale
factor. `compute_semantic_density()` (new) is RFC-MM003v2's `D_s ∈ [0, 1]`,
which becomes `MeaningMeasurement.density`. These are not interchangeable
and are not unified — see the module docstring in `density_estimation.py`.

### 3.3 `Σ = σ²_input · (B·Bᵀ)` and where `σ²_input` comes from

RFC-MM003v2 SS4 gives the propagation formula but never specifies
`σ²_input`'s source. This repository sets `σ²_input := 1 / density.value`
(the pre-existing evidence-density scalar from SS3.2 above), which is not
an arbitrary choice: Local Frame Resolution's whitening basis satisfies
`B · g · Bᵀ = I` by construction, which means `B · Bᵀ = g⁻¹` exactly. The
pre-v2-alignment covariance formula was `Σ = g⁻¹ / density.value` — i.e.
`Σ = (1/density.value) · (B·Bᵀ)` was already the behavior, just derived from
`g` directly instead of from `B`. Re-expressing it in RFC-MM003's canonical
`σ²_input · (B·Bᵀ)` form using `σ²_input = 1/density.value` is therefore a
pure notational alignment, not a behavior change — verified by
`test_estimate_covariance_equals_scaled_metric_inverse` in
[`tests/test_covariance.py`](../tests/test_covariance.py), which asserts the
new formula's output equals the old `inverse(g)/density` formula bit-for-bit
(within floating-point tolerance).

## 4. Non-Discontinuity Guard default (RFC-MM004v2 SS4)

`Δmax` has no RFC-specified numeric value. `THETA_DISCONTINUITY_MAX = 10.0`
([`_constants.py`](../src/meaning_mapper/_constants.py)) is an experimental
default, chosen on the same order of magnitude as the existing
`THETA_BOUND_SCALE` topology bound rather than an unrelated arbitrary
constant. Callers may override it via
`map_observation(..., discontinuity_delta_max=...)`.

## 5. `MeaningMapperPipeline` (RFC-MM004v2 SS2)

Added as the RFC-named entry point (`MeaningMapperPipeline().process(...)`).
`map_observation()` — the pre-existing, tested public function — is kept as
a thin delegate to it, so no existing caller's import breaks.
`MeasurementResult.is_valid` (RFC-MM002v2 SS3 naming) was added alongside
the pre-existing `is_quarantined` (its logical negation), for the same
non-breaking reason.

## 6. Defensive Tuple Locking (RFC-MM002v2 SS4.2)

`MetricTensor.matrix`, `LocalFrame.basis`/`.metric_tensor`, and
`Covariance.matrix` were `numpy.ndarray` fields on otherwise-`frozen=True`
dataclasses — `frozen=True` blocks attribute *reassignment* but not in-place
mutation of a mutable field's contents, so this was a real immutability gap
independent of the v2 realignment, not just an RFC-naming mismatch. All
three now store `Matrix` (`tuple[tuple[float, ...], ...]`), frozen via
`__post_init__` (`freeze_matrix`, see
[`_linalg.py`](../src/meaning_mapper/_linalg.py)) regardless of whether the
constructor received an `ndarray`, a nested list, or an already-frozen
tuple. A `.array` property reconstructs the mutable `ndarray` view on demand
for internal linear algebra; nothing outside `_linalg.py` holds a live
mutable reference to ABI state.

## 7. Verification status (2026-08-04)

pytest 98 passed, 100% line + branch coverage, `ruff check`/`ruff format
--check` clean, `mypy --strict` clean (24 source files). See `CHANGELOG.md`
for the version this shipped in.

## 8. Temporal context and the time-aware guard (additive; not in RFC-MM001v2-005v2)

Two additions, neither of which changes what is measured or any existing output:

**Declared temporal context.** `semantic.metadata.time_frame` -- a JSON object, the T06
`time_frame` of the annotation standard (absolute / relative / actor / historical / future)
-- is carried onto `MeaningMeasurement.temporal_context` and out through `as_dict()`.
It is *excluded* from the hashed features, so `theta`, `sigma`, `density` and
`measurement_id` are identical with or without it; it is covered by `provenance_hash`
(mixed in only when present, so every measurement without one keeps its previous hash).
Only its shape is validated (a JSON object, string keys, finite JSON values); whether the
dates are right, and which role each plays, is the annotator's responsibility. A malformed
value is quarantined at validation. `ValidatedObservation.metadata` is left whole so
`meaning_mapper.cle.grounding` keeps forwarding it unmodified.

**Time-aware Non-Discontinuity Guard.** RFC-MM004v2 SS4 judges the jump
`||theta_t - theta_(t-1)||` against a fixed `Delta_max` and has no notion of time. When the
caller passes `previous_timestamp_ns` **and** an explicit `discontinuity_rate_max`, the jump
is judged as a rate (theta units per second over the elapsed time). There is no default
`rate_max`: no numeric bound is specified anywhere, so none is invented. Passing neither
keeps SS4 exactly. Edge cases: `dt < 0` is quarantined (not in time order); `dt == 0` has no
rate and falls back to the displacement rule. `timestamp_ns` here is the observation's
seal time (`final_seal.sealed_at`), i.e. the *observation* clock -- the subject's and
historical times are what `temporal_context` carries, not what orders measurements.
