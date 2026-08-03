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
- Categorical Lift (internal stage of the measurement pipeline)
- Topological Consistency Check
- Generating a MeaningMeasurement

**Must not**

- Hold runtime state
- Update MSR's internal state
- Provide long-term memory
- Manage HEKB
- Generate goals
- Generate intent
- Make policy decisions
- Implement control logic
- Control NVS-Kernel
- Call an LLM
- Generate prompts
- Render language

## No independent Categorical Lift component

Categorical Lift is implemented as
[`src/meaning_mapper/lift/categorical_lift.py`](../src/meaning_mapper/lift/categorical_lift.py),
one stage in Meaning Mapper's pipeline. There is no `cle/`,
`categorical-lift/`, standalone "CLE Engine" module, library, or repository,
and none should be added. Categorical Lift's extensibility (toward a
functor, natural transformation, pullback, pushout, or commutative diagram)
is expressed as a `typing.Protocol` other lift implementations can satisfy
in-process — not as a new component with its own boundary.

## Ecosystem responsibility table

| Component | Input | Output | Owns | Must not |
|---|---|---|---|---|
| `semantic-annotator-core` | MeasuredObservation | HEXT Observation | Normalization, schema, ABI | Meaning measurement, memory, runtime, control |
| **Meaning Mapper** | HEXT Observation | MeaningMeasurement | Geometric measurement, Categorical Lift | Runtime, memory, control, language |
| MSR (`meaning-space-runtime`) | MeaningMeasurement | Runtime Meaning State | Meaning-space state, time evolution, potential field, drift | Observation parsing, measurement, memory |
| HEKB | — | — | Long-term memory, concepts, semantic structure | Runtime, measurement, control |
| NVS-Kernel | — | — | Control, reflex, feedback, trajectory | Observation, measurement, language |
| Kernel Executive | — | — | Goal, intent, planning, governance | Measurement, runtime, memory |
| LLM | — | — | Natural language rendering, code rendering, prior knowledge | Source of truth, runtime authority, measurement authority |

## Crossings are structural, not shared imports

Meaning Mapper does not import `semantic-annotator-core` or `msr`.
`HEXTObservation` (`src/meaning_mapper/types.py`) is a `Mapping[str, Any]`
describing the subset of the HEXT JSON shape this repo reads, not a shared
class. `MeaningMeasurement` (`src/meaning_mapper/measurement/`) is
field-for-field structurally identical to `msr.abi.MeaningMeasurement` and
`.as_dict()`-compatible with `msr.adapters.mapper.measurement_from_payload`,
but is Meaning Mapper's own type. This mirrors RFC-MSR01 Section 4: "any
object satisfying a port's shape MAY be bound" — the contract is a shape, not
a shared dependency.
