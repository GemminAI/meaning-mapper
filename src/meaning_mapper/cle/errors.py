"""CLE adapter error hierarchy.

Mirrors this repo's own `errors.py` convention (plain exception classes,
no external error-handling framework) rather than importing a pattern
from another repository. Distinguishes three failure modes a caller needs
to tell apart: no response at all, an HTTP error response, and a 200
response that does not match the schema this adapter expects.
"""

from __future__ import annotations

from typing import Any


class CLEClientError(Exception):
    """Base error for all CLE adapter failures."""


class CLEUnreachableError(CLEClientError):
    """Connection refused, DNS failure, or timeout -- no HTTP response received."""


class CLEHTTPError(CLEClientError):
    """CLE returned a non-2xx HTTP response."""

    def __init__(self, status_code: int, body: Any):
        self.status_code = status_code
        self.body = body
        super().__init__(f"CLE returned HTTP {status_code}: {body}")


class CLESchemaError(CLEClientError):
    """A 200 response did not contain the fields this adapter requires."""

    def __init__(self, detail: str, body: Any):
        self.detail = detail
        self.body = body
        super().__init__(f"CLE response schema mismatch: {detail}")
