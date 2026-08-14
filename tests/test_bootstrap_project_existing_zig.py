#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = (
    ROOT
    / "evals"
    / "workspaces"
    / "bootstrap-project"
    / "existing-zig-baseline"
)
SCRIPT = (
    ROOT
    / "skills"
    / "development"
    / "workflows"
    / "bootstrap-project"
    / "scripts"
    / "baseline_existing_zig.py"
)
PRESERVED = ("README.md", "build.zig", "build.zig.zon", "src/root.zig")


class BaselineExistingZigTest(unittest.TestCase):
    def test_completes_the_ziwei_style_baseline_without_touching_source(self) -> None:
        result = self.run_baseline()

        self.assertEqual(0, result["completed"].returncode, result["completed"].stderr)
        target = result["target"]
        report = result["report"]
        expected = json.loads((FIXTURE / "expected.json").read_text(encoding="utf-8"))
        self.assertEqual("completed", report["status"])
        self.assertEqual(expected["versions"], report["versions"])
        self.assertEqual(expected["changes"], report["changes"])
        self.assert_preserved(result["before"], target)

        mise_source = (target / "mise.toml").read_text(encoding="utf-8")
        self.assertIn('zig = "0.16.0"', mise_source)
        self.assertIn('lefthook = "2.1.10"', mise_source)
        for task in ("format", "format-check", "lint", "check", "test", "build", "ci"):
            self.assertIn(f"[tasks.{task}]", mise_source)

        lefthook_source = (target / "lefthook.yml").read_text(encoding="utf-8")
        order = [
            lefthook_source.index("partial-stage-guard"),
            lefthook_source.index("format-staged-zig"),
            lefthook_source.index("lint-staged-zig"),
            lefthook_source.index("quick-project-check"),
        ]
        self.assertEqual(sorted(order), order)
        self.assertNotIn("parallel: true", lefthook_source)
        self.assertNotIn("zig build test", lefthook_source)
        self.assertEqual(
            [
                ["install"],
                ["exec", "--", "lefthook", "install", "--force"],
                ["run", "ci"],
            ],
            [entry["argv"] for entry in result["commands"]],
        )

    def test_blocks_cross_file_zig_version_mismatch_before_writes(self) -> None:
        result = self.run_baseline(
            mutate=lambda target: (target / "build.zig.zon").write_text(
                (target / "build.zig.zon")
                .read_text(encoding="utf-8")
                .replace('"0.16.0"', '"0.15.2"'),
                encoding="utf-8",
            )
        )

        self.assertNotEqual(0, result["completed"].returncode)
        self.assertEqual("blocked", result["report"]["status"])
        self.assertIn("version", result["report"]["error"].lower())
        self.assertEqual([], result["commands"])
        self.assert_preserved(result["before"], result["target"])

    def test_blocks_an_alternative_environment_manager_before_writes(self) -> None:
        result = self.run_baseline(
            mutate=lambda target: (target / ".tool-versions").write_text(
                "zig 0.16.0\n",
                encoding="utf-8",
            )
        )

        self.assertNotEqual(0, result["completed"].returncode)
        self.assertEqual("blocked", result["report"]["status"])
        self.assertTrue(
            any(
                ".tool-versions" in conflict
                for conflict in result["report"]["conflicts"]
            )
        )
        self.assertEqual([], result["commands"])
        self.assert_preserved(result["before"], result["target"])

    def test_blocks_unknown_lefthook_content_instead_of_overwriting_it(self) -> None:
        def add_unknown_job(target: Path) -> None:
            lefthook = target / "lefthook.yml"
            lefthook.write_text(
                lefthook.read_text(encoding="utf-8")
                + "\ncommit-msg:\n  commands:\n    custom:\n      run: ./custom-check\n",
                encoding="utf-8",
            )

        result = self.run_baseline(mutate=add_unknown_job)

        self.assertNotEqual(0, result["completed"].returncode)
        self.assertEqual("blocked", result["report"]["status"])
        self.assertTrue(
            any(
                "lefthook.yml" in conflict
                for conflict in result["report"]["conflicts"]
            )
        )
        self.assertEqual([], result["commands"])
        self.assertIn(
            "./custom-check",
            (result["target"] / "lefthook.yml").read_text(encoding="utf-8"),
        )

    def test_blocks_an_unknown_mise_hook_before_running_it(self) -> None:
        def replace_hook(target: Path) -> None:
            mise = target / "mise.toml"
            mise.write_text(
                mise.read_text(encoding="utf-8").replace(
                    'postinstall = "lefthook install"',
                    'postinstall = "./unknown-install"',
                ),
                encoding="utf-8",
            )

        result = self.run_baseline(mutate=replace_hook)

        self.assertNotEqual(0, result["completed"].returncode)
        self.assertEqual("blocked", result["report"]["status"])
        self.assertIn("postinstall", result["report"]["error"])
        self.assertEqual([], result["commands"])

    def test_reports_ci_failure_as_partial_with_recovery(self) -> None:
        result = self.run_baseline(fail_on="run ci")

        self.assertNotEqual(0, result["completed"].returncode)
        report = result["report"]
        self.assertEqual("partial", report["status"])
        self.assertEqual([str(result["fake_mise"]), "run", "ci"], report["failed_command"])
        self.assertEqual("failed", report["verification"]["mise_run_ci"])
        self.assertIn("rerun", report["recovery"])
        self.assertEqual(
            [
                ".github/renovate.json",
                ".github/workflows/validate.yml",
                ".lefthook/partial-stage-guard.sh",
                "mise.lock",
            ],
            report["changes"]["created"],
        )
        self.assert_preserved(result["before"], result["target"])

    def test_reports_install_and_hook_failures_as_partial(self) -> None:
        for failed in (
            ["install"],
            ["exec", "--", "lefthook", "install", "--force"],
        ):
            with self.subTest(failed=failed):
                result = self.run_baseline(fail_on=" ".join(failed))
                report = result["report"]

                self.assertNotEqual(0, result["completed"].returncode)
                self.assertEqual("partial", report["status"])
                self.assertEqual([str(result["fake_mise"]), *failed], report["failed_command"])
                self.assertIn("adapter", report["recovery"])
                self.assert_preserved(result["before"], result["target"])

    def test_completed_baseline_is_idempotent(self) -> None:
        result = self.run_baseline()
        self.assertEqual(0, result["completed"].returncode, result["completed"].stderr)
        second_report = result["root"] / "second-report.json"

        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--target",
                str(result["target"]),
                "--mise",
                str(result["fake_mise"]),
                "--report",
                str(second_report),
            ],
            cwd=ROOT,
            env=result["environment"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(0, completed.returncode, completed.stderr)
        report = json.loads(second_report.read_text(encoding="utf-8"))
        self.assertEqual(
            {"created": [], "modified": [], "deleted": []},
            report["changes"],
        )
        self.assert_preserved(result["before"], result["target"])

    def run_baseline(
        self,
        *,
        mutate=None,
        fail_on: str = "",
    ) -> dict[str, object]:
        temporary = tempfile.TemporaryDirectory(prefix="bootstrap-existing-zig-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        target = root / "project"
        shutil.copytree(FIXTURE / "input", target)
        subprocess.run(
            ["git", "-C", str(target), "init"],
            check=True,
            capture_output=True,
            text=True,
        )
        if mutate is not None:
            mutate(target)
        before = {path: self.digest(target / path) for path in PRESERVED}
        log_path = root / "commands.jsonl"
        report_path = root / "report.json"
        fake_mise = root / "fake_mise.py"
        fake_mise.write_text(
            textwrap.dedent(
                f"""\
                #!{sys.executable}
                import json
                import os
                from pathlib import Path
                import sys

                args = sys.argv[1:]
                cwd = Path.cwd()
                with Path(os.environ["FAKE_MISE_LOG"]).open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps({{"argv": args, "cwd": str(cwd)}}) + "\\n")
                if " ".join(args) == os.environ.get("FAKE_MISE_FAIL_ON"):
                    print("forced mise failure", file=sys.stderr)
                    raise SystemExit(7)
                if args == ["install"]:
                    (cwd / "mise.lock").write_text(
                        '[[tools.lefthook]]\\nversion = "2.1.10"\\n\\n'
                        '[[tools.zig]]\\nversion = "0.16.0"\\n',
                        encoding="utf-8",
                    )
                elif args == ["exec", "--", "lefthook", "install", "--force"]:
                    hooks = cwd / ".git" / "hooks"
                    hooks.mkdir(parents=True, exist_ok=True)
                    hook = hooks / "pre-commit"
                    hook.write_text("LEFTHOOK installed\\n", encoding="utf-8")
                    hook.chmod(0o755)
                elif args == ["run", "ci"]:
                    required = [
                        "mise.toml",
                        "lefthook.yml",
                        ".lefthook/partial-stage-guard.sh",
                        ".github/workflows/validate.yml",
                        ".github/renovate.json",
                    ]
                    if any(not (cwd / path).exists() for path in required):
                        raise SystemExit(8)
                """
            ),
            encoding="utf-8",
        )
        fake_mise.chmod(0o755)
        environment = os.environ.copy()
        environment.update(
            {
                "FAKE_MISE_FAIL_ON": fail_on,
                "FAKE_MISE_LOG": str(log_path),
            }
        )
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--target",
                str(target),
                "--mise",
                str(fake_mise),
                "--report",
                str(report_path),
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        commands = (
            [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
            if log_path.is_file()
            else []
        )
        return {
            "before": before,
            "commands": commands,
            "completed": completed,
            "fake_mise": fake_mise,
            "environment": environment,
            "report": json.loads(report_path.read_text(encoding="utf-8")),
            "root": root,
            "target": target,
        }

    def assert_preserved(self, before: dict[str, str], target: Path) -> None:
        self.assertEqual(before, {path: self.digest(target / path) for path in PRESERVED})

    def digest(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
