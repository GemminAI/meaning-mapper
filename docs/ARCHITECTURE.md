# Architecture

Meaning Mapper is a single deterministic measurement pipeline. It has one
public entry point, `meaning_mapper.map_observation`, and one output shape,
`MeasurementResult` (exactly one of `.measurement` or `.quarantine` is set).

```text
HEXTObservation
      |
      v
[1] Observation Validation      -> ValidatedObservation | QuarantineReason
      |
      v
[2] Metric Tensor Estimation    -> MetricTensor | QuarantineReason
      |
      v
[3] Local Frame Resolution      -> LocalFrame                (bootstraps, never fails)
      |
      v
[4] Density Estimation          -> Density                   (never fails; always clamped)
      |
      v
[5] Covariance Estimation       -> Covariance
      |
      v
[6] Categorical Lift            -> theta: tuple[float, ...]  (internal stage)
      |
      v
[7] Topological Consistency     -> None | QuarantineReason
      |
      v
[8] MeaningMeasurement Generation -> MeaningMeasurement
```

## Stage responsibilities

| Stage | Module | Input | Output |
|---|---|---|---|
| 1. Observation Validation | `validation/observation_validation.py` | `HEXTObservation` | `ValidatedObservation` (id, text, metadata, content hash, timestamp, raw features) |
| 2. Metric Tensor Estimation | `metrics/metric_tensor.py` | raw features | `MetricTensor` — SPD, diagonal, eigenvalue-clamped |
| 3. Local Frame Resolution | `frame/local_frame.py` | `MetricTensor` | `LocalFrame` — orthonormal whitening basis, bootstraps to identity when needed |
| 4. Density Estimation | `density/density_estimation.py` | raw features | `Density` — clamped scalar |
| 5. Covariance Estimation | `covariance/covariance_estimation.py` | `MetricTensor`, `Density` | `Covariance` — SPD, eigenvalue-clamped |
| 6. Categorical Lift | `lift/categorical_lift.py` | raw features, `LocalFrame` | `theta` |
| 7. Topological Consistency Check | `topology/topological_consistency.py` | `theta`, `LocalFrame`, `Covariance` | pass, or `QuarantineReason` |
| 8. MeaningMeasurement Generation | `measurement/meaning_measurement.py`, `pipeline.py` | everything above | `MeaningMeasurement` |

## Why this order

Metric Tensor Estimation runs on the *raw* (pre-lift) feature space, not on
`theta` — there is no `theta` yet at that point. It estimates how much a unit
step in each raw coordinate should count (dense, frequently-seen coordinates
count for less). Local Frame Resolution turns that metric into an
orthonormal basis. Density and Covariance Estimation build the uncertainty
that basis implies. Only then does Categorical Lift place the observation's
raw features *in* that frame to get `theta` — so `theta` and `Sigma` are
computed in a mutually consistent local geometry by construction, and
Topological Consistency Check is what verifies that construction actually
held (dimensions agree, nothing is non-finite, `theta` is not absurdly far
from what its own `Sigma` would predict).

## Determinism

No stage calls an external model, reads wall-clock time, or holds state
across observations. Raw feature extraction (`_features.py`) uses the
hashing trick (SHA-256-bucketed token counts) instead of a learned embedding.
`timestamp_ns` comes from the HEXT Observation's own `final_seal.sealed_at`
or `ledger[0].t`, never from `time.time()`. Two calls to `map_observation`
with the same observation always produce bit-identical output.

## Failure handling

Per RFC-MM001 Principle 5 (Optional), `map_observation` never raises for a
rejected observation. A stage that cannot proceed returns a
`QuarantineReason` (which stage, why, which observation) instead of an
exception, and the pipeline returns a quarantined `MeasurementResult`. The
caller's observation loop is expected to continue.

`InvariantError` is a separate, narrower channel: it is raised by
`Covariance.validate()` / `MeaningMeasurement.validate()` for callers who
construct those types directly (outside `map_observation`) and get a
genuinely broken value — a programmer-error class of defect, not a
data-driven rejection.
