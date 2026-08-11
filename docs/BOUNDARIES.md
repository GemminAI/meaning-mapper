# Boundaries

Boundary before algorithm. If a responsibility below is not listed under
**Owns**, Meaning Mapper does not implement it — it is delegated to whichever
neighbor owns it.

## Meaning Mapper

**Input:** HEXT Observation
**Output:** MeaningMeasurement

**Owns**

- Receiving a HEXT Observation
- Observation Validation
- Metric Tensor Estimation
- Local Frame Resolution
- Density Estimation
- Covariance Estimation
- Semantic Projection (placing raw features in the local frame to get `theta`)
- Topological Consistency Check
- Generating a MeaningMeasurement

**Must not**

- Hold runtime state
- Update MSR's internal state
- Provide long-term memory
- Manage HEKB or commit to HEKB
- Generate Concepts
- Generate Categories
- Perform Knowledge Crystallization
- Perform Homotopy Analysis
- Generate goals
- Generate intent
- Make policy decisions
- Implement control logic
- Control NVS-Kernel
- Call an LLM
- Generate prompts
- Render language

Meaning Mapper is a measurement instrument: it produces one
position-plus-uncertainty reading (`theta`, `sigma`) per observation and
stops. Anything past that — interpreting a *sequence* of measurements,
discovering a stable concept, crystallizing knowledge, or touching HEKB — is
Categorical Lift Engine's job, not Meaning Mapper's. This split is
deliberate product architecture (OSS measurement vs. Pro knowledge
generation), not an implementation detail; see
[`docs/RFC_COMPLIANCE.md`](RFC_COMPLIANCE.md).

## Categorical Lift Engine (CLE) is an independent component

CLE is **not** part of this repository. It previously was (2026-08-04
rebuild), and that decision was reverted the same day once the product
architecture — OSS (`semantic-annotator-core` + Meaning Mapper + MSR) / Pro
(CLE) / Enterprise (HEKB Cloud) — made clear that measurement and knowledge
generation are different products, not just different modules. See
`CHANGELOG.md` for both changes.

**Input:** `MeaningMeasurement` or `StabilizedTrajectory`
**Output:** `Concept`, `Knowledge Delta`, `HEKB Commit`

**Owns**

- Categorical Lift (the categorical-theory construction: functor, natural
  transformation, pullback, pushout, commutative diagram)
- Stable trajectory interpretation
- Concept discovery
- Knowledge crystallization
- Category evolution
- HEKB integration

**Must not**

- Perform geometric measurement (Meaning Mapper's job)
- Evolve runtime meaning-space state (MSR's job)
- Issue control decisions (NVS-Kernel's job)

Do not add a categorical-theory *implementation* (functors, pullbacks, or
any of CLE's own algorithms) to *this* repository.
`src/meaning_mapper/projection/semantic_projection.py` is Semantic
Projection — a fixed, non-extensible geometric step that produces
`theta` — and is deliberately not designed as a seam toward functors,
pullbacks, or other categorical-theory machinery. That extensibility now
belongs entirely to CLE, in its own repository.

**`meaning_mapper.cle` (added 2026-08-12) is not that module.** It is an
HTTP-only *client* to CLE's independent service — `client.py`
(`CLEClient`, one method per CLE endpoint), `models.py` (wire-format
dataclasses, hand-kept in sync with CLE's own OpenAPI schema), and
`grounding.py` (`ground_observation`: HEXT Observation → CLE `/ground`,
preserving the source Observation's identity/provenance alongside CLE's
response). It reimplements no CLE algorithm — every method builds a
request, sends it over HTTP, and parses the response. This does not
revise the "no cle/ module" decision above: no `import cle` (CLE's own
Python package) exists anywhere in this repository; `meaning_mapper.cle`
is this repository's *own* adapter code, the same relationship
`meaning_mapper.types.HEXTObservation` already has to
`semantic-annotator-core` — a structural port, not a shared dependency.

## Ecosystem responsibility table

| Component | Input | Output | Owns | Must not |
|---|---|---|---|---|
| `semantic-annotator-core` | MeasuredObservation | HEXT Observation | Normalization, schema, ABI | Meaning measurement, memory, runtime, control |
| **Meaning Mapper** | HEXT Observation | MeaningMeasurement | Geometric measurement, Semantic Projection | Runtime, memory, control, language, concept/category generation |
| MSR (`meaning-space-runtime`) | MeaningMeasurement | Runtime Meaning State; `StabilizedTrajectory` to CLE | Meaning-space state, time evolution, potential field, drift | Observation parsing, measurement, memory |
| Categorical Lift Engine (CLE) | MeaningMeasurement / StabilizedTrajectory | Concept, Knowledge Delta, HEKB Commit | Categorical Lift, trajectory interpretation, concept discovery, knowledge crystallization | Measurement, runtime state evolution, control |
| HEKB | — | — | Long-term memory, concepts, semantic structure | Runtime, measurement, control |
| NVS-Kernel | — | — | Control, reflex, feedback, trajectory | Observation, measurement, language |
| Kernel Executive | — | — | Goal, intent, planning, governance | Measurement, runtime, memory |
| LLM | — | — | Natural language rendering, code rendering, prior knowledge | Source of truth, runtime authority, measurement authority |

## Crossings are structural, not shared imports

Meaning Mapper does not import `semantic-annotator-core` or `msr` (and, now
that CLE is independent again, would not import a `cle` package either).
`HEXTObservation` (`src/meaning_mapper/types.py`) is a `Mapping[str, Any]`
describing the subset of the HEXT JSON shape this repo reads, not a shared
class. `MeaningMeasurement` (`src/meaning_mapper/measurement/`) is
field-for-field structurally identical to `msr.abi.MeaningMeasurement` and
`.as_dict()`-compatible with `msr.adapters.mapper.measurement_from_payload`,
but is Meaning Mapper's own type. This mirrors RFC-MSR01 Section 4: "any
object satisfying a port's shape MAY be bound" — the contract is a shape, not
a shared dependency, and the same convention applies at the MSR/CLE boundary.
