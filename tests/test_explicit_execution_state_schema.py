#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = (
    ROOT
    / "skills"
    / "development"
    / "workflows"
    / "explicit-execution-state"
)
SCRIPTS = SKILL / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from statectl_runtime.errors import StateError
from statectl_runtime.model import pointer_parts


class ExplicitExecutionStateSchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        action_schema = json.loads(
            (SKILL / "references" / "schemas" / "action.schema.json").read_text(
                encoding="utf-8"
            )
        )
        cls.path_schema = action_schema["properties"]["preconditions"]["items"][
            "properties"
        ]["path"]

    def test_action_precondition_paths_match_runtime_json_pointer_contract(self) -> None:
        cases = {
            "/a": True,
            "/a/~0/~1": True,
            "": False,
            "/": False,
            "/a//b": False,
            "/a/~2": False,
            "a": False,
        }

        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(expected, self.public_schema_accepts(path))
                self.assertEqual(expected, self.runtime_accepts(path))

    @classmethod
    def public_schema_accepts(cls, value: object) -> bool:
        if cls.path_schema.get("type") == "string" and not isinstance(value, str):
            return False
        pattern = cls.path_schema.get("pattern")
        return pattern is None or re.search(pattern, value) is not None

    @staticmethod
    def runtime_accepts(value: object) -> bool:
        try:
            pointer_parts(value, require_patchable=False)
        except StateError:
            return False
        return True


if __name__ == "__main__":
    unittest.main()
