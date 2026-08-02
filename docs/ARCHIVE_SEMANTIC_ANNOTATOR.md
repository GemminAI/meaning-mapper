# Archive note: `GemminAI/semantic-annotator`

## Status

**Archived historical experimental infrastructure.**  
No further feature development will occur in `GemminAI/semantic-annotator`.

## What it was

`GemminAI/semantic-annotator` was a **private experimental scaffold** (v0.1.0) created to explore a narrow Observation → AnnotatedObservation pipeline for SensOS OCI experiments (including planned SA001 RunPod baseline work).

It provided:

- toy / deterministic annotators (`PassthroughAnnotator`, `KeywordAnnotator`)
- an NDJSON CLI and Dockerfile scaffold
- architecture notes for a swappable `Annotator` protocol

It was **not** the production SensOS meaning-attachment service, and it was **not** the public HEXT normalization reference library.

## What supersedes it

| Role | Canonical home |
|------|----------------|
| Product / reference service | [`GemminAI/meaning-mapper`](https://github.com/GemminAI/meaning-mapper) (**Meaning Mapper**) |
| Reference library (normalization RI) | [`GemminAI/semantic-annotator-core`](https://github.com/GemminAI/semantic-annotator-core) |
| Open Standards | [`GemminAI/sensos-docs`](https://github.com/GemminAI/sensos-docs) / https://sensos.org/Open-Standards |
| Reference runtime | [`GemminAI/nvs-runtime`](https://github.com/GemminAI/nvs-runtime) |

## Preservation

- Historical commits remain preserved in the archived repository for audit and research continuity.
- Design intent that remains valid (stateless transform, swappable strategy behind a narrow contract, streaming-friendly I/O) is carried forward under the **Meaning Mapper** product identity and the Core RI library.
- Experimental LLM / RunPod plans from the scaffold are **not** part of the Meaning Mapper 1.0 open reference surface.

## Policy

- Do not open new features against the archived scaffold.
- Do not cite the scaffold as the current product name in customer or partner materials.
- For migration steps, see [`MIGRATION.md`](MIGRATION.md).
