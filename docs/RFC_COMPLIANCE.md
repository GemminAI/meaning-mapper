# RFC Compliance

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

## What this repository actually claims

- Input: HEXT Observation (structural, not a shared import from
  `semantic-annotator-core`).
- Output: `MeaningMeasurement`, structurally compatible with
  `msr.abi.MeaningMeasurement` / RFC-MSR01 Section 2.
- Categorical Lift is internal (RFC-MM series' successor text, once written,
  should keep it that way — no independent `cle` component; see
  [`docs/BOUNDARIES.md`](BOUNDARIES.md)).
- Deterministic, LLM-independent, no runtime state, no control logic.
