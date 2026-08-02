# Refactoring Report — Meaning Mapper v1.0 RFC Completion

## Summary

Repositioned Meaning Mapper from a thin HEXT CLI wrapper into the canonical
RFC-SA001–SA005 Reference Service implementation.

## Files added

| File | Purpose |
|------|---------|
| `src/meaning_mapper/abi/*` | SA002 AnnotationView ABI |
| `src/meaning_mapper/payload/*` | SA003 schema |
| `src/meaning_mapper/mapper/*` | AnnotationMapper |
| `src/meaning_mapper/runtime_bridge.py` | SA004/005 bridges + DTO confinement |
| `src/meaning_mapper/engine/*` | Replaceable deterministic engine |
| `tests/test_sa00{2,3,4,5}_*.py` | Verification matrices |
| `docs/RFC_COMPLIANCE.md` | Compliance matrix |
| `docs/REFACTORING_REPORT.md` | This report |
| `examples/sa005_request.json` | SA005 sample request |

## Files modified

| File | Change |
|------|--------|
| `src/meaning_mapper/service.py` | SA005 API; `/map` product; deprecated `/annotate` |
| `src/meaning_mapper/cli.py` | `annotate` default + `hext` subcommand |
| `src/meaning_mapper/__init__.py` | Public ABI exports |
| `docs/ARCHITECTURE.md` | SA architecture diagram |
| `README.md` | Product docs match implementation |
| `CHANGELOG.md` | v1.0 RFC completion notes |
| `examples/basic.py` | SA pipeline example |

## Removed / retired drift

| Item | Action |
|------|--------|
| HEXT-only `POST /map` body (`document`/`source_type`) | Replaced with SA005 request layout |
| `GET /adapters` product endpoint | Removed from SA surface (use Core / `hext`) |
| Scaffold “Semantic Annotator” product framing | Superseded; Core remains library name |
| Experimental LLM paths | Not present; model-independent engine only |

## Compatibility

- `POST /annotate` retained, marked **Deprecated**
- CLI bare input still runs annotate
- `meaning-mapper hext` preserves Core HEXT normalize
- Package `semantic-annotator-core` **not renamed**
