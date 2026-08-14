#!/usr/bin/env python3

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_workspace_evals.py"


class RunWorkspaceEvalsTest(unittest.TestCase):
    def test_read_only_plan_records_an_unchanged_workspace(self) -> None:
        result = self.run_case(mutate=False)

        self.assertEqual(0, result["completed"].returncode, result["completed"].stderr)
        report = result["report"]
        self.assertEqual("passed", report["status"])
        self.assertEqual(report["workspace"]["before"], report["workspace"]["after"])
        self.assertEqual(
            {"created": [], "modified": [], "deleted": []},
            report["workspace"]["changes"],
        )
        self.assertIn("--sandbox", report["execution"]["command"])
        sandbox_index = report["execution"]["command"].index("--sandbox")
        self.assertEqual(
            "workspace-write",
            report["execution"]["command"][sandbox_index + 1],
        )
        self.assertEqual("captured stdout\n", report["execution"]["stdout"])
        self.assertEqual("captured stderr\n", report["execution"]["stderr"])
        self.assertIn("$bootstrap-project-working-tree-eval", result["prompt"])

    def test_unexpected_mutation_is_captured_and_fails_the_case(self) -> None:
        result = self.run_case(mutate=True)

        self.assertNotEqual(0, result["completed"].returncode)
        report = result["report"]
        self.assertEqual("failed", report["status"])
        self.assertEqual(["generated.txt"], report["workspace"]["changes"]["created"])
        self.assertEqual(["README.md"], report["workspace"]["changes"]["modified"])
        self.assertEqual(
            ["src/root.zig"],
            report["workspace"]["changes"]["deleted"],
        )
        self.assertTrue(
            any("unexpected workspace changes" in failure for failure in report["failures"])
        )

    def run_case(self, *, mutate: bool) -> dict[str, object]:
        with tempfile.TemporaryDirectory(prefix="workspace-eval-test-") as directory:
            directory_path = Path(directory)
            prompt_path = directory_path / "prompt.txt"
            report_directory = directory_path / "reports"
            fake_codex_path = directory_path / "fake_codex.py"
            fake_codex_path.write_text(
                textwrap.dedent(
                    f"""\
                    #!{sys.executable}
                    import os
                    from pathlib import Path
                    import sys

                    output_index = sys.argv.index("--output-last-message")
                    cwd_index = sys.argv.index("--cd")
                    workspace = Path(sys.argv[cwd_index + 1])
                    Path(os.environ["PROMPT_CAPTURE_PATH"]).write_text(
                        sys.stdin.read(),
                        encoding="utf-8",
                    )
                    if os.environ["EVAL_MUTATE"] == "true":
                        readme = workspace / "README.md"
                        readme.write_text(
                            readme.read_text(encoding="utf-8") + "changed\\n",
                            encoding="utf-8",
                        )
                        (workspace / "generated.txt").write_text(
                            "generated\\n",
                            encoding="utf-8",
                        )
                        (workspace / "src" / "root.zig").unlink()
                    Path(sys.argv[output_index + 1]).write_text(
                        os.environ["EVAL_RESPONSE"],
                        encoding="utf-8",
                    )
                    print("captured stdout")
                    print("captured stderr", file=sys.stderr)
                    """
                ),
                encoding="utf-8",
            )
            fake_codex_path.chmod(0o755)

            environment = os.environ.copy()
            environment.update(
                {
                    "EVAL_MUTATE": str(mutate).lower(),
                    "EVAL_RESPONSE": (
                        "Mode: existing. Stack: Zig. Shape: library. "
                        "Plan: preserve the source and version pins; report conflicts "
                        "before apply."
                    ),
                    "PROMPT_CAPTURE_PATH": str(prompt_path),
                }
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--skill",
                    "bootstrap-project",
                    "--case",
                    "existing-zig-planning",
                    "--codex",
                    str(fake_codex_path),
                    "--report-dir",
                    str(report_directory),
                    "--timeout",
                    "5",
                ],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            report = json.loads(
                (report_directory / "existing-zig-planning.json").read_text(
                    encoding="utf-8"
                )
            )
            return {
                "completed": completed,
                "prompt": prompt_path.read_text(encoding="utf-8"),
                "report": report,
            }


if __name__ == "__main__":
    unittest.main()
