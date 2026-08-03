from __future__ import annotations

import numpy as np

from meaning_mapper._features import raw_features


def test_raw_features_is_deterministic() -> None:
    first = raw_features("the quick brown fox", {"lang": "en"})
    second = raw_features("the quick brown fox", {"lang": "en"})
    assert np.array_equal(first, second)


def test_raw_features_ignores_metadata_key_order() -> None:
    ordered = raw_features("hello world", {"a": "1", "b": "2"})
    reordered = raw_features("hello world", {"b": "2", "a": "1"})
    assert np.array_equal(ordered, reordered)


def test_raw_features_empty_text_and_metadata_is_zero_vector() -> None:
    vector = raw_features("", {})
    assert np.array_equal(vector, np.zeros(8))


def test_raw_features_dimension_matches_argument() -> None:
    vector = raw_features("some words here", {}, dimension=16)
    assert vector.shape == (16,)


def test_raw_features_differs_for_different_text() -> None:
    first = raw_features("alpha beta gamma", {})
    second = raw_features("delta epsilon zeta", {})
    assert not np.array_equal(first, second)
