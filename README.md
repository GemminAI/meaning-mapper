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
| **Output** | `MeaningMeasurement` (`measurement_id`, `observation_id`, `frame_id`, `theta`, `sigma`, `timestamp_ns`, `density`, `provenance`, `provenance_hash`) |
| **Downstream** | [`meaning-space-runtime`](https://github.com/GemminAI/meaning-space-runtime) (RFC-MSR01) |
| **License** | Apache-2.0 |
| **Version** | 2.3.0 |
| **Spec** | RFC-MM001v2–RFC-MM005v2 (see [`docs/RFC_ALIGNMENT.md`](docs/RFC_ALIGNMENT.md)) |

## What it does

Runs one deterministic measurement pipeline, in order:

1. **Observation Validation** — receive and check a HEXT Observation.
2. **Metric Tensor Estimation** — a local SPD metric `g` over raw features.
3. **Local Frame Resolution** — an orthonormal basis (whitening frame) for `g`.
4. **Density Estimation** — a clamped local evidence-density scalar, and the
   entropy-based semantic density `D_s` (RFC-MM003).
5. **Covariance Estimation** — `Sigma = sigma_input^2 * (B @ B.T)` (RFC-MM003),
   where `B` is the local frame's whitening basis.
6. **Semantic Projection** *(fixed geometric step, not Categorical Lift)* —
   projects raw features through the local frame into `theta`.
7. **Topological Consistency Check** — theta, frame, and Sigma must agree.
   An optional, stateless Non-Discontinuity Guard (RFC-MM004) also runs here
   if the caller supplies `previous_theta` — Meaning Mapper never retains it.
8. **MeaningMeasurement Generation** — package the result.

Every stage is pure and deterministic: no model calls, no wall-clock
randomness, no shared runtime state between observations. See
[`docs/RFC_ALIGNMENT.md`](docs/RFC_ALIGNMENT.md) for exactly where this
implementation follows RFC-MM001v2–RFC-MM005v2 and where/why it
intentionally deviates.

## What it does not do

Runtime state, MSR's internal state, long-term memory, HEKB (including HEKB
commits), Concept generation, Category generation, Knowledge Crystallization,
Homotopy Analysis, goal/intent generation, policy decisions, control logic,
NVS-Kernel control, LLM calls, prompt generation, or language rendering.
Everything past a single measurement — interpreting a *sequence* of
measurements into knowledge — belongs to the independent Categorical Lift
Engine (CLE), not this repository. See
[`docs/BOUNDARIES.md`](docs/BOUNDARIES.md) for the full Owns / Must Not list.

This repository does not implement Semantic Grounding, Categorical Lift,
Pullback, Recovery, or Compression either — `meaning_mapper.cle` (below)
only calls CLE's independent HTTP service for those; it reimplements none
of them.

## CLE Adapter (`meaning_mapper.cle`)

An HTTP-only client to CLE, the independent Categorical Lift Engine
service. Two things it is not: it is not CLE (no CLE algorithm is
reimplemented — every method builds a request, sends it, and parses the
response); and it is not a change to what Meaning Mapper measures — the
existing pipeline above is untouched.

```python
from meaning_mapper import map_observation
from meaning_mapper.cle.client import CLEClient
from meaning_mapper.cle.grounding import ground_observation
from meaning_mapper.cle.models import ConceptInput
from meaning_mapper.errors import QuarantineReason

client = CLEClient("http://localhost:8300")

# Semantic Grounding of a real Observation. `goal` is always caller-supplied
# — no ecosystem component currently produces one, and none is fabricated
# here (see docs/BOUNDARIES.md for why this stays a required parameter).
result = ground_observation(client, observation, goal="stabilize trajectory")
if isinstance(result, QuarantineReason):
    print(result)  # observation itself was unusable; CLE was never called
else:
    print(result.observation_id, result.grounded.semantic_state.sok)

# Or: feed a real MeaningMeasurement's theta into CLE's /lift directly.
measurement_result = map_observation(observation)
if measurement_result.is_valid:
    lift = client.lift(ConceptInput.from_measurement(measurement_result.measurement))
```

`CLEClient` covers CLE's full HTTP surface: `health`, `ground`, `lift`,
`pullback`, `recover`, `compress` — verified against CLE's own live
`/openapi.json`, not assumed. See
[`src/meaning_mapper/cle/`](src/meaning_mapper/cle/) and
[`docs/BOUNDARIES.md`](docs/BOUNDARIES.md) for the full contract and boundary.

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
        +--------------------------------------------+
        v                                            v
MeaningMeasurement                    meaning_mapper.cle (this repo's
        |                              HTTP adapter, added 2026-08-12)
        v                                            |
Meaning Space Runtime (RFC-MSR01)     <- OSS / free   v
        |                                   Categorical Lift Engine
        v                                   (separate repository)  <- Pro
StabilizedTrajectory                                  |
        |                                              v
        v                                        GroundedState / LiftResult
Categorical Lift Engine (separate repository)         <- Pro
        |
        v
Concept
        |
        v
HEKB                                                  <- Enterprise: HEKB Cloud
```

The right-hand path is new (2026-08-12): `meaning_mapper.cle.grounding.
ground_observation` sends the *original HEXT Observation's text* to CLE's
`/ground`; `ConceptInput.from_measurement` sends the *measured*
`MeaningMeasurement.theta` to CLE's `/lift`. Both are additive — neither
replaces the existing MSR path on the left, and MSR/StabilizedTrajectory
are unaffected.

Meaning Mapper does not import `semantic-annotator-core`, `msr`, or CLE's
own `cle` Python package. Every crossing is a structural port (a plain
`Mapping`/dataclass shape) or, for the new CLE adapter, a plain HTTP call —
matching RFC-MSR01 Section 4, the same convention MSR itself uses at every
boundary, including the MSR/CLE crossing above.

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
