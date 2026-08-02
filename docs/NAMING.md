# Naming plan

## Canonical product identity

| Surface | Canonical value |
|---------|-----------------|
| Product brand | **Meaning Mapper** |
| GitHub repository | `GemminAI/meaning-mapper` |
| Python package | `meaning-mapper` |
| Import package | `meaning_mapper` |
| CLI | `meaning-mapper` |
| Docker image | `gemminai/meaning-mapper` |
| Compose service | `meaning-mapper` |
| HTTP service id | `meaning-mapper` |
| Canonical API | `POST /map` |
| SDK helper | `meaning_mapper.map_observation(...)` |

## Historical / library names (retained where needed)

| Surface | Value | Policy |
|---------|-------|--------|
| Library repo | `GemminAI/semantic-annotator-core` | Keep — RI library identity |
| Library PyPI/package name | `semantic-annotator` | Keep until a major library rename (avoid breakage) |
| Library CLI | `semantic-annotator` | Library-only; product CLI is `meaning-mapper` |
| Library Docker | `gemminai/semantic-annotator-core` | Keep for library consumers |
| Private scaffold | `GemminAI/semantic-annotator` | **Archived** — no further development |
| Compat CLI shim | `semantic-annotator` entry in Meaning Mapper | Deprecated warning → remove in 2.0 |
| Compat HTTP | `POST /annotate` | Deprecated → remove in 2.0 |

## Terminology guidance

| Prefer | Avoid in new product docs |
|--------|---------------------------|
| Meaning Mapper | Semantic Annotator (except migration notes) |
| map / mapping / projection | annotate / annotation (except wire compatibility) |
| HEXT Observation Object | informal “annotated blob” language |
| reference service | “experimental scaffold” |
| Open Standards alignment | enterprise kernel metaphors |

## Rename checklist (shipping)

- [x] Repository description: Meaning Mapper reference service
- [x] README title and examples
- [x] `pyproject.toml` package + scripts
- [x] CLI prog name `meaning-mapper`
- [x] Docker image `gemminai/meaning-mapper`
- [x] Compose project/service names
- [x] `/map` canonical endpoint
- [x] Migration + archive docs
- [ ] Publish container registry tags (ops follow-up)
- [ ] Optional: PyPI publish of `meaning-mapper` (ops follow-up)
