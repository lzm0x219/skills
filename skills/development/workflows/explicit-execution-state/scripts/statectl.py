#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import sys


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))

from statectl_runtime.cli import main
from statectl_runtime.model import (
    ACTION_KEYS,
    PATCH_OPERATIONS,
    PRECONDITION_OPERATORS,
    RECEIPT_KEYS,
    RECEIPT_STATUSES,
    STATE_KEYS,
)


if __name__ == "__main__":
    raise SystemExit(main())
