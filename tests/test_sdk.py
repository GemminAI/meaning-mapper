# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

from meaning_mapper import __version__, map_observation


def test_version() -> None:
    assert __version__ == "1.0.0"


def test_map_observation() -> None:
    obj = map_observation({"event": "boot", "device": "sensor-1"})
    assert "object" in obj
    assert "id" in obj["object"]
