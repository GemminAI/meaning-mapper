# Changelog

## 1.0.0 — 2026-08-02

### Added

- Meaning Mapper product identity superseding the archived private `semantic-annotator` scaffold
- Package `meaning-mapper`, CLI `meaning-mapper`, Docker image `gemminai/meaning-mapper`
- Canonical HTTP endpoint `POST /map`
- Compatibility shims: deprecated CLI `semantic-annotator`, deprecated `POST /annotate`
- Positioning, architecture, boundaries, naming, migration, and archive documentation
- Service-surface tests and CI (lint, test, Docker build)

### Notes

- Normalization engine is provided by `semantic-annotator-core` v1.0.0 (library RI)
- No LLM inference, storage, or enterprise runtime control in this release
