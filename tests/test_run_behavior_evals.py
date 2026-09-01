#!/usr/bin/env python3

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_behavior_evals.py"


class RunBehaviorEvalsTest(unittest.TestCase):
    def test_workspace_only_case_is_excluded_from_read_only_runner(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--skill",
                "explicit-execution-state",
                "--answers",
                "evals/fixtures/explicit-execution-state",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("PASS: 6 behavior case(s).", completed.stdout)
        self.assertNotIn("statectl-workspace-init", completed.stdout)

    def test_workspace_only_case_rejects_direct_behavior_selection(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--skill",
                "explicit-execution-state",
                "--case",
                "statectl-workspace-init",
                "--answers",
                "evals/fixtures/explicit-execution-state",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(0, completed.returncode)
        self.assertIn("must use run_workspace_evals.py", completed.stderr)

    def test_out_of_scope_case_does_not_explicitly_invoke_the_skill(self) -> None:
        result = self.run_case(
            "out-of-scope-direct-answer",
            'Change the first line of the README to "Toolset".',
        )

        self.assertNotIn("$napi-rs-working-tree-eval", result["prompt"])

    def test_in_scope_case_explicitly_invokes_the_skill(self) -> None:
        result = self.run_case(
            "generic-binding-design",
            "The JavaScript contract uses an adapter layer and returns stable, machine-readable errors. Then run Node integration tests.",
        )

        self.assertIn("$napi-rs-working-tree-eval", result["prompt"])

    def test_live_evaluation_isolates_codex_and_user_skill_homes(self) -> None:
        result = self.run_case(
            "generic-binding-design",
            "The JavaScript contract uses an adapter layer and returns stable, machine-readable errors. Then run Node integration tests.",
        )

        self.assertNotEqual(result["source_codex_home"], result["eval_codex_home"])
        self.assertNotEqual(result["source_user_home"], result["eval_user_home"])
        self.assertEqual("test-auth", result["eval_auth"])
        self.assertFalse(result["eval_codex_skills_exist"])
        self.assertFalse(result["eval_user_skills_exist"])
        self.assertFalse(result["eval_codex_home"].exists())
        self.assertFalse(result["eval_user_home"].exists())

    def run_case(self, case_id: str, response: str) -> dict[str, object]:
        with tempfile.TemporaryDirectory(prefix="run-behavior-evals-test-") as directory:
            directory_path = Path(directory)
            prompt_path = directory_path / "prompt.txt"
            codex_home_capture_path = directory_path / "codex-home.txt"
            source_codex_home = directory_path / "source-codex-home"
            source_user_home = directory_path / "source-user-home"
            (source_codex_home / "skills" / "napi-rs").mkdir(parents=True)
            (source_user_home / ".agents" / "skills" / "napi-rs").mkdir(parents=True)
            (source_codex_home / "auth.json").write_text("test-auth", encoding="utf-8")
            (source_codex_home / "skills" / "napi-rs" / "SKILL.md").write_text(
                "installed copy",
                encoding="utf-8",
            )
            (
                source_user_home / ".agents" / "skills" / "napi-rs" / "SKILL.md"
            ).write_text("installed copy", encoding="utf-8")

            fake_codex_path = directory_path / "fake_codex.py"
            fake_codex_path.write_text(
                textwrap.dedent(
                    f"""\
                    #!{sys.executable}
                    import os
                    from pathlib import Path
                    import sys

                    try:
                        output_index = sys.argv.index("--output-last-message")
                    except ValueError:
                        raise SystemExit("missing --output-last-message")

                    codex_home = Path(os.environ["CODEX_HOME"])
                    user_home = Path(os.environ["HOME"])
                    Path(os.environ["PROMPT_CAPTURE_PATH"]).write_text(
                        sys.stdin.read(),
                        encoding="utf-8",
                    )
                    values = [
                        str(codex_home),
                        str(user_home),
                        (codex_home / "auth.json").read_text(encoding="utf-8"),
                        str((codex_home / "skills").exists()).lower(),
                        str((user_home / ".agents" / "skills").exists()).lower(),
                    ]
                    Path(os.environ["CODEX_HOME_CAPTURE_PATH"]).write_text(
                        "\\n".join(values),
                        encoding="utf-8",
                    )
                    Path(sys.argv[output_index + 1]).write_text(
                        os.environ["EVAL_RESPONSE"],
                        encoding="utf-8",
                    )
                    """
                ),
                encoding="utf-8",
            )
            fake_codex_path.chmod(0o755)

            environment = os.environ.copy()
            environment.update(
                {
                    "CODEX_HOME": str(source_codex_home),
                    "CODEX_HOME_CAPTURE_PATH": str(codex_home_capture_path),
                    "HOME": str(source_user_home),
                    "PROMPT_CAPTURE_PATH": str(prompt_path),
                    "EVAL_RESPONSE": response,
                }
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(RUNNER),
                    "--skill",
                    "napi-rs",
                    "--case",
                    case_id,
                    "--codex",
                    str(fake_codex_path),
                    "--timeout",
                    "5",
                ],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            (
                eval_codex_home,
                eval_user_home,
                eval_auth,
                eval_codex_skills_exist,
                eval_user_skills_exist,
            ) = codex_home_capture_path.read_text(encoding="utf-8").splitlines()
            return {
                "prompt": prompt_path.read_text(encoding="utf-8"),
                "source_codex_home": source_codex_home,
                "source_user_home": source_user_home,
                "eval_codex_home": Path(eval_codex_home),
                "eval_user_home": Path(eval_user_home),
                "eval_auth": eval_auth,
                "eval_codex_skills_exist": eval_codex_skills_exist == "true",
                "eval_user_skills_exist": eval_user_skills_exist == "true",
            }


if __name__ == "__main__":
    unittest.main()
