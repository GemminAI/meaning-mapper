# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Gemmina Intelligence LLC.

"""Minimal Meaning Mapper SDK example."""

from meaning_mapper import map_observation

obj = map_observation({"event": "boot", "device": "sensor-1"})
print(obj["object"]["id"])
