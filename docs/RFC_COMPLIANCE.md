# RFC Compliance

> **2026-08-04 update**: RFC-MM001v2–RFC-MM005v2 ("Post-Implementation
> Realignment") now supersede the v1 `AnnotationView` ABI text referenced
> throughout this document as the "known sync gap." That gap is
> substantially closed as of v2.2.0 — see
> [`docs/RFC_ALIGNMENT.md`](RFC_ALIGNMENT.md) for the current, authoritative
> conformance matrix and deviation log. The section below is kept for
> historical context on *why* the v1 gap existed.

## RFC-MSR01 (Meaning Space Runtime) — the binding contract

[RFC-MSR01](https://github.com/GemminAI/meaning-space-runtime/blob/main/RFC-MSR01.md)
is **Verified** (95 tests, 100% coverage, mypy strict, ruff clean) and names
Meaning Mapper as its sole upstream: `MeaningMeasurement` (`observation_id`,
`frame_id`, `theta`, `sigma`, `timestamp_ns`, `provenance`) crossing
Meaning Mapper -> MSR via a structural port
(`msr.adapters.mapper.measurement_from_payload`). This repository's output
type and pipeline exist to satisfy that contract; see
[`docs/BOUNDARIES.md`](BOUNDARIES.md) for the exact field-shape mapping.

## RFC-SA001–SA005 / RFC-MM001–MM005 — known sync gap

As of 2026-08-02, the canonical, published RFC-MM001–MM005 documents (in
`sensos-docs/docs/rfc/`, superseding RFC-SA001–SA005) describe a different
architecture than this repository implements: an `AnnotationView` /
`AnnotatedObservation` ABI service (Meaning View ABI, Meaning Payload Schema,
Meaning Runtime Bridge, Meaning Mapper Service API) that receives
*MeasuredObservation* directly and never mentions HEXT Observations, a
metric tensor, or a `MeaningMeasurement` output.

That architecture is what the pre-2026-08-04 version of this repository
implemented (100% RFC-SA/MM compliant against the *old* text) and is now
preserved under [`legacy/rfc-sa-annotation-service/`](../legacy/rfc-sa-annotation-service/README.md).

This is a documentation/implementation sync gap, not a claim that the legacy
code is current: RFC-MSR01 (verified, already built) requires the
`theta`/`sigma` measurement shape this repository now produces, and the
implementation-first workflow used across this ecosystem (Implementation ->
Experiment -> Verification -> RFC) means the RFC-MM001–MM005 text is expected
to catch up to this implementation, not the other way around. Updating
`sensos-docs/docs/rfc/RFC-MM001.md`–`RFC-MM005.md` and
`RFCv3_draft/rfc/MM/` is out of scope for this repository and was not
requested here — flagged for a separate RFC-authoring pass.

## Product-tier alignment (2026-08-04, reverted same day)

Earlier the same day, Categorical Lift was integrated into Meaning Mapper as
an internal pipeline stage. That decision was reverted a few hours later:
SensOS's product architecture is tiered — OSS/free (`semantic-annotator-core`
+ Meaning Mapper + MSR, fully usable with no cloud dependency), Pro
(Categorical Lift Engine — trajectory interpretation, concept discovery,
knowledge crystallization, HEKB integration), and Enterprise (HEKB Cloud,
governance, team sync) — and that split is a business-architecture fact, not
an implementation detail MM can absorb. The software boundary now mirrors it:
MM stops at a single measurement; CLE, an independent component, is what
turns a *sequence* of measurements into knowledge. Neither reversion changed
the RFC-MM001–MM005 / RFC-MSR01 sync-gap situation above — this is a second,
independent note about a decision that was made and then reverted entirely
within this repository's own history, not a further RFC drift.

## What this repository actually claims

- Input: HEXT Observation (structural, not a shared import from
  `semantic-annotator-core`).
- Output: `MeaningMeasurement`, structurally compatible with
  `msr.abi.MeaningMeasurement` / RFC-MSR01 Section 2.
- Semantic Projection (placing raw features in the local frame to get
  `theta`) is internal and fixed; Categorical Lift itself — and any future
  RFC-CLE series — belongs to the independent Categorical Lift Engine, not
  this repository. See [`docs/BOUNDARIES.md`](BOUNDARIES.md).
- Deterministic, LLM-independent, no runtime state, no control logic.
