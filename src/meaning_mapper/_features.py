"""Deterministic raw feature extraction from a validated observation's content.

Uses the hashing trick (a fixed-width feature-hashed bag of tokens) rather
than a learned embedding: no model call, no external state, and the same
text always hashes to the same vector. This keeps Meaning Mapper
LLM-independent and reproducible (RFC-MM001 Principle 3).
"""

from __future__ import annotations

import hashlib
import re

import numpy as np

from meaning_mapper._constants import MEANING_SPACE_DIMENSION
from meaning_mapper._linalg import FloatArray

_TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


def _bucket(token: str, dimension: int) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % dimension


def _scatter(tokens: list[str], dimension: int) -> FloatArray:
    vector = np.zeros(dimension, dtype=np.float64)
    for token in tokens:
        vector[_bucket(token, dimension)] += 1.0
    return vector


def raw_features(
    text: str,
    metadata: dict[str, object],
    *,
    dimension: int = MEANING_SPACE_DIMENSION,
) -> FloatArray:
    """Hash ``text`` tokens and canonicalized ``metadata`` pairs into ``R^dimension``.

    Metadata keys are sorted before hashing so insertion order never affects
    the result (Reproducible, RFC-MM001 Principle 3).
    """
    text_tokens = [token.lower() for token in _TOKEN_PATTERN.findall(text)]
    meta_tokens = [f"meta:{key}={metadata[key]!r}" for key in sorted(metadata)]
    return _scatter(text_tokens, dimension) + _scatter(meta_tokens, dimension)
