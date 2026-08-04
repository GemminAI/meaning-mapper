# Meaning Mapper

**The SensOS Meaning Measurement engine.**

Meaning Mapper measures. It takes a HEXT Observation and produces a
`MeaningMeasurement` — a position `theta` in local meaning-space coordinates,
with a declared uncertainty `sigma` — for [Meaning Space Runtime
(MSR)](https://github.com/GemminAI/meaning-space-runtime) to consume. It does
not annotate, hold runtime state, control anything, or render language. See
[`docs/BOUNDARIES.md`](docs/BOUNDARIES.md).

| | |
|---|---|
| **Product** | Meaning Mapper |
| **Repository** | [`GemminAI/meaning-mapper`](https://github.com/GemminAI/meaning-mapper) |
| **Python package** | `meaning-mapper` |
| **Input** | HEXT Observation (from `semantic-annotator-core`) |
| **Output** | `MeaningMeasurement` (`theta`, `sigma`, `frame_id`, `observation_id`, `timestamp_ns`, `provenance`) |
| **Downstream** | [`meaning-space-runtime`](https://github.com/GemminAI/meaning-space-runtime) (RFC-MSR01) |
| **License** | Apache-2.0 |
| **Version** | 2.1.0 |

## What it does

Runs one deterministic measurement pipeline, in order:

1. **Observation Validation** — receive and check a HEXT Observation.
2. **Metric Tensor Estimation** — a local SPD metric `g` over raw features.
3. **Local Frame Resolution** — an orthonormal basis (whitening frame) for `g`.
4. **Density Estimation** — a clamped local evidence-density scalar.
5. **Covariance Estimation** — `Sigma`, the metric inverse scaled by density.
6. **Semantic Projection** *(fixed geometric step, not Categorical Lift)* —
   projects raw features through the local frame into `theta`.
7. **Topological Consistency Check** — theta, frame, and Sigma must agree.
8. **MeaningMeasurement Generation** — package the result.

Every stage is pure and deterministic: no model calls, no wall-clock
randomness, no shared runtime state between observations.

## What it does not do

Runtime state, MSR's internal state, long-term memory, HEKB (including HEKB
commits), Concept generation, Category generation, Knowledge Crystallization,
Homotopy Analysis, goal/intent generation, policy decisions, control logic,
NVS-Kernel control, LLM calls, prompt generation, or language rendering.
Everything past a single measurement — interpreting a *sequence* of
measurements into knowledge — belongs to the independent Categorical Lift
Engine (CLE), not this repository. See
[`docs/BOUNDARIES.md`](docs/BOUNDARIES.md) for the full Owns / Must Not list.

## Quick start

```bash
pip install -e ".[dev]"
pytest
```

```python
from meaning_mapper import map_observation

observation = {
    "object": {"id": "obs-1"},
    "evidence": {"body": "the quick brown fox jumps over the lazy dog"},
    "semantic": {"metadata": {}},
    "final_seal": {"sealed_at": "2026-08-04T00:00:00Z", "state_hash": "a" * 64},
    "provenance": {"contributors": [{"agent": "software:semantic-annotator@1.0.0"}]},
}

result = map_observation(observation)
if result.is_quarantined:
    print(result.quarantine)  # QuarantineReason(stage=..., detail=..., ...)
else:
    measurement = result.measurement
    print(measurement.theta, measurement.sigma)
    # measurement.as_dict() is accepted by
    # msr.adapters.mapper.measurement_from_payload directly.
```

## Ecosystem

```text
MeasuredObservation
        |
        v
semantic-annotator-core                              <- OSS / free
        |
        v
HEXT Observation
        |
        v
Meaning Mapper (this repo)                            <- OSS / free
    Validation -> Metric Tensor -> Local Frame -> Density
        -> Covariance -> Semantic Projection -> Topology -> Measurement
        |
        v
MeaningMeasurement
        |
        v
Meaning Space Runtime (RFC-MSR01)                     <- OSS / free
        |
        v
StabilizedTrajectory
        |
        v
Categorical Lift Engine (separate repository)         <- Pro
        |
        v
Concept
        |
        v
HEKB                                                  <- Enterprise: HEKB Cloud
```

Meaning Mapper does not import `semantic-annotator-core` or `msr`. Every
crossing is a structural port (a plain `Mapping`/dataclass shape), matching
RFC-MSR01 Section 4 — the same convention MSR itself uses at every boundary,
including the MSR/CLE crossing above.

## Semantic Projection, not Categorical Lift

Meaning Mapper's stage 6
([`src/meaning_mapper/projection/semantic_projection.py`](src/meaning_mapper/projection/semantic_projection.py))
is **Semantic Projection**: a fixed, purely geometric linear projection
through the local frame that produces `theta`. It is deliberately not an
extension seam toward category theory (functor, natural transformation,
pullback/pushout, commutative diagram) — that machinery is **Categorical
Lift**, owned entirely by the independent Categorical Lift Engine (CLE), a
separate repository and product tier. See
[`docs/BOUNDARIES.md`](docs/BOUNDARIES.md).

## Documentation

| Doc | Purpose |
|-----|---------|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Pipeline and stage responsibilities |
| [`docs/BOUNDARIES.md`](docs/BOUNDARIES.md) | Owns / Must Not, ecosystem responsibility table |
| [`docs/RFC_COMPLIANCE.md`](docs/RFC_COMPLIANCE.md) | RFC alignment and a known RFC/implementation sync gap |

## Tests

```bash
pytest             # 100% line + branch coverage enforced (fail_under = 100)
ruff check src tests
mypy               # strict, src/
```

## License

Apache License 2.0 — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
