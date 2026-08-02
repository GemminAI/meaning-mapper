# Repository boundaries

## Owns

- RFC-SA001–SA005 Reference Service implementation
- Meaning Mapper product identity (CLI, Docker, `/map`)
- Domain-neutral ABI (`AnnotationView`, `AnnotatedObservation`)
- Runtime Bridge confinement zone (`runtime_bridge.py`)
- Deterministic default annotator engine

## Does not own

| Concern | Owner |
|---------|-------|
| HEXT normalization algorithms | [`semantic-annotator-core`](https://github.com/GemminAI/semantic-annotator-core) |
| HEXT normative schema | [HEXT-AI/hxt-spec](https://github.com/HEXT-AI/hxt-spec) |
| Open Standards RFCs | [`sensos-docs`](https://github.com/GemminAI/sensos-docs) |
| Reference runtime | [`nvs-runtime`](https://github.com/GemminAI/nvs-runtime) |
| Enterprise evaluation / control | `nvs-kernel` / SensOS commercial (private) |

## Forbidden

- NVS-Kernel / HEKB / SensOS commercial imports
- DAK, Execution Algebra, proprietary control-plane logic
- LLM provider SDKs in the default engine
- Importing `RuntimeAnnotationDTO` outside `runtime_bridge.py`
- Importing `httpx` / `requests` inside `abi/`, `mapper/`, `payload/`, `engine/`

## AST enforcement

See `tests/test_sa002_abi.py` (`test_dto_confinement_ast`, `test_boundary_purity_ast`).
