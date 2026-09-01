#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
STATECTL = (
    ROOT
    / "skills"
    / "development"
    / "workflows"
    / "durable-execution-state"
    / "scripts"
    / "statectl.py"
)


class DurableExecutionStateLongHorizonTest(unittest.TestCase):
    def test_one_hundred_transitions_keep_only_the_current_plan_value(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="durable-execution-state-long-horizon-"
        ) as temporary:
            root = Path(temporary)
            store = root / "store"
            criteria = root / "criteria.json"
            patch = root / "patch.json"
            criteria.write_text(
                json.dumps([{"id": "done", "description": "Task is done"}]),
                encoding="utf-8",
            )
            self.run_statectl(
                "init",
                "--store",
                str(store),
                "--task-id",
                "long-horizon",
                "--objective",
                "Keep bounded current state",
                "--criteria-file",
                str(criteria),
            )

            for version in range(100):
                operation = "add" if version == 0 else "replace"
                patch.write_text(
                    json.dumps(
                        [
                            {
                                "op": operation,
                                "path": "/plan/current",
                                "value": {
                                    "step": version + 1,
                                    "source_ref": f"log://observation/{version + 1}",
                                },
                            }
                        ]
                    ),
                    encoding="utf-8",
                )
                self.run_statectl(
                    "apply-patch",
                    "--store",
                    str(store),
                    "--expected-version",
                    str(version),
                    "--patch-file",
                    str(patch),
                )

            state = self.run_statectl("show", "--store", str(store))
            replay = self.run_statectl("replay", "--store", str(store))
            verified = self.run_statectl("verify", "--store", str(store))

            self.assertEqual(100, state["state_version"])
            self.assertEqual(
                {"step": 100, "source_ref": "log://observation/100"},
                state["plan"]["current"],
            )
            self.assertEqual(101, replay["event_count"])
            self.assertGreater(replay["state_size_bytes"], 0)
            self.assertLessEqual(replay["state_size_bytes"], 64 * 1024)
            self.assertTrue(replay["replayed"])
            self.assertTrue(verified["verified"])

    def run_statectl(self, *arguments: str) -> dict[str, object]:
        result = subprocess.run(
            [sys.executable, str(STATECTL), *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)


if __name__ == "__main__":
    unittest.main()
