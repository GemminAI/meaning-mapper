"""HTTP-only adapter to CLE (Categorical Lift Engine). Meaning Mapper
retains Measurement/Projection; CLE retains Semantic Grounding, Lift,
Pullback, Recover, Compress -- this package calls CLE's API, it does not
reimplement any of CLE's algorithms."""

from __future__ import annotations

from meaning_mapper.cle.client import CLEClient
from meaning_mapper.cle.errors import (
    CLEClientError,
    CLEHTTPError,
    CLESchemaError,
    CLEUnreachableError,
)
from meaning_mapper.cle.grounding import (
    GroundedObservation,
    GroundingContext,
    extract_grounding_context,
    ground_observation,
)
from meaning_mapper.cle.models import (
    SOK,
    CompositionEntry,
    CompressionResult,
    ConceptInput,
    FiniteCategoryInput,
    FiveW1H,
    FiveW1HField,
    FiveW1HOverrides,
    GroundedState,
    GroundResult,
    InvariantSignature,
    LiftResult,
    Morphism,
    ProofCertificate,
    PullbackResult,
    RecoveredContext,
    SOKOverrides,
)

__all__ = [
    "SOK",
    "CLEClient",
    "CLEClientError",
    "CLEHTTPError",
    "CLESchemaError",
    "CLEUnreachableError",
    "CompositionEntry",
    "CompressionResult",
    "ConceptInput",
    "FiniteCategoryInput",
    "FiveW1H",
    "FiveW1HField",
    "FiveW1HOverrides",
    "GroundResult",
    "GroundedObservation",
    "GroundedState",
    "GroundingContext",
    "InvariantSignature",
    "LiftResult",
    "Morphism",
    "ProofCertificate",
    "PullbackResult",
    "RecoveredContext",
    "SOKOverrides",
    "extract_grounding_context",
    "ground_observation",
]
