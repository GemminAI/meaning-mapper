# Legacy: RFC-SA Annotation Service

This directory preserves the pre-2026-08-04 implementation of `meaning-mapper`,
which built an `AnnotationView` / `AnnotatedObservation` ABI service against
RFC-SA001–SA005 (superseded by RFC-MM001–MM005 in name, but not in shape).

It is retained for reference only and is **not** part of the current build
(`pyproject.toml` no longer includes this tree). The current `src/` implements
Meaning Mapper as the geometric measurement engine required by
[RFC-MSR01](https://github.com/GemminAI/meaning-space-runtime/blob/main/RFC-MSR01.md):
`HEXT Observation -> MeaningMeasurement (theta, sigma)`.

The published RFC-MM001–MM005 documents (in `sensos-docs/docs/rfc/`) still
describe this legacy annotation-ABI architecture as of 2026-08-02 — that is a
known RFC/implementation sync gap, not a claim that this legacy code is
current. See the root `CHANGELOG.md` for details.
