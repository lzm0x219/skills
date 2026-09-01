from __future__ import annotations

import os

from .errors import StateError


FAULT_ENVIRONMENT_VARIABLE = "STATECTL_FAULT_POINT"


def inject_fault(point: str) -> None:
    """Raise at a named transaction boundary when explicitly enabled by tests."""
    if os.environ.get(FAULT_ENVIRONMENT_VARIABLE) == point:
        raise StateError(f"fault injected at {point}")

