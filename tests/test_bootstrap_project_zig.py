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
SCRIPT = (
    ROOT
    / "skills"
    / "development"
    / "workflows"
    / "bootstrap-project"
    / "scripts"
    / "bootstrap_zig.py"
)


class BootstrapZigTest(unittest.TestCase):
    def test_creates_a_library_from_the_official_initializer_boundary(self) -> None:
        result = self.run_bootstrap("library")

        self.assertEqual(0, result["completed"].returncode, result["completed"].stderr)
        target = result["target"]
        report = result["report"]
        self.assertEqual("completed", report["status"])
        self.assertEqual(
            {
                "lefthook": "passed",
                "mise_run_ci": "passed",
                "no_commit": "passed",
            },
            report["verification"],
        )
        self.assertTrue((target / "src" / "root.zig").is_file())
        self.assertFalse((target / "src" / "main.zig").exists())
        self.assertIn("b.addLibrary", (target / "build.zig").read_text(encoding="utf-8"))
        self.assertIn(
            ".fingerprint = 0x1234abcd",
            (target / "build.zig.zon").read_text(encoding="utf-8"),
        )
        self.assert_common_baseline(target)
        self.assert_command_order(result["commands"])
        self.assert_initializer_boundary(report, target)
        self.assert_repository_has_no_commit(target)

    def test_creates_a_cli_with_an_executed_smoke_test(self) -> None:
        result = self.run_bootstrap("cli")

        self.assertEqual(0, result["completed"].returncode, result["completed"].stderr)
        target = result["target"]
        self.assertTrue((target / "src" / "main.zig").is_file())
        self.assertFalse((target / "src" / "root.zig").exists())
        build_source = (target / "build.zig").read_text(encoding="utf-8")
        self.assertIn("b.addExecutable", build_source)
        self.assertIn("b.addRunArtifact", build_source)
        self.assertIn('b.step("test", "Run tests")', build_source)
        self.assert_common_baseline(target)
        self.assert_repository_has_no_commit(target)

    def test_refuses_a_non_empty_target_before_running_tools(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bootstrap-zig-non-empty-") as directory:
            root = Path(directory)
            target = root / "project"
            target.mkdir()
            existing = target / "owned.txt"
            existing.write_text("keep\n", encoding="utf-8")
            result = self.invoke(root, target, "library")

            self.assertNotEqual(0, result["completed"].returncode)
            self.assertEqual("keep\n", existing.read_text(encoding="utf-8"))
            self.assertEqual("blocked", result["report"]["status"])
            self.assertEqual([], result["commands"])

    def test_refuses_a_symlink_target_before_running_tools(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bootstrap-zig-symlink-") as directory:
            root = Path(directory)
            linked = root / "linked"
            linked.mkdir()
            target = root / "project"
            target.symlink_to(linked, target_is_directory=True)

            result = self.invoke(root, target, "library")

            self.assertNotEqual(0, result["completed"].returncode)
            self.assertEqual("blocked", result["report"]["status"])
            self.assertEqual([], result["commands"])
            self.assertEqual([], list(linked.iterdir()))

    def test_refuses_a_report_path_inside_the_target_without_writing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bootstrap-zig-report-") as directory:
            target = Path(directory) / "project"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--target",
                    str(target),
                    "--name",
                    "sample_project",
                    "--shape",
                    "library",
                    "--zig-version",
                    "0.16.0",
                    "--lefthook-version",
                    "2.1.10",
                    "--report",
                    str(target / "report.json"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(2, completed.returncode)
            self.assertIn("--report must be outside", completed.stderr)
            self.assertFalse(target.exists())

    def test_reports_the_failed_command_and_keeps_partial_evidence(self) -> None:
        result = self.run_bootstrap("library", fail_on="run ci")

        self.assertNotEqual(0, result["completed"].returncode)
        report = result["report"]
        self.assertEqual("partial", report["status"])
        self.assertEqual([str(result["fake_mise"]), "run", "ci"], report["failed_command"])
        self.assertEqual("failed", report["verification"]["mise_run_ci"])
        self.assertIn("rerun", report["recovery"])
        self.assertTrue((result["target"] / "mise.toml").is_file())
        self.assertTrue(report["commands"])

    def test_partial_stage_guard_stops_before_formatting(self) -> None:
        result = self.run_bootstrap("library")

        self.assertEqual(0, result["completed"].returncode, result["completed"].stderr)
        target = result["target"]
        source = target / "src" / "root.zig"
        subprocess.run(
            ["git", "-C", str(target), "add", "src/root.zig"],
            check=True,
            capture_output=True,
            text=True,
        )
        source.write_text(
            source.read_text(encoding="utf-8") + "\n// unstaged change\n",
            encoding="utf-8",
        )

        completed = subprocess.run(
            [str(target / ".lefthook" / "partial-stage-guard.sh")],
            cwd=target,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(0, completed.returncode)
        self.assertIn("both staged and unstaged changes", completed.stderr)
        staged = subprocess.run(
            ["git", "-C", str(target), "show", ":src/root.zig"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertNotIn("unstaged change", staged)

    def run_bootstrap(self, shape: str, *, fail_on: str = "") -> dict[str, object]:
        temporary = tempfile.TemporaryDirectory(prefix=f"bootstrap-zig-{shape}-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        target = root / "project"
        return self.invoke(root, target, shape, fail_on=fail_on)

    def invoke(
        self,
        root: Path,
        target: Path,
        shape: str,
        *,
        fail_on: str = "",
    ) -> dict[str, object]:
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
                elif args == ["exec", "--", "zig", "init"]:
                    (cwd / "src").mkdir(exist_ok=True)
                    (cwd / "build.zig").write_text("official build\\n", encoding="utf-8")
                    (cwd / "build.zig.zon").write_text(
                        '.{{\\n    .name = .official,\\n    .fingerprint = 0x1234abcd,\\n}}\\n',
                        encoding="utf-8",
                    )
                    (cwd / "src" / "main.zig").write_text("official main\\n", encoding="utf-8")
                    (cwd / "src" / "root.zig").write_text("official root\\n", encoding="utf-8")
                elif args == ["exec", "--", "lefthook", "install", "--force"]:
                    hooks = cwd / ".git" / "hooks"
                    hooks.mkdir(parents=True, exist_ok=True)
                    (hooks / "pre-commit").write_text("installed\\n", encoding="utf-8")
                    (hooks / "pre-commit").chmod(0o755)
                elif args == ["run", "ci"]:
                    required = [
                        "build.zig",
                        "build.zig.zon",
                        "mise.toml",
                        "lefthook.yml",
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
                "--name",
                "sample_project",
                "--shape",
                shape,
                "--zig-version",
                "0.16.0",
                "--lefthook-version",
                "2.1.10",
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
            "commands": commands,
            "completed": completed,
            "fake_mise": fake_mise,
            "report": json.loads(report_path.read_text(encoding="utf-8")),
            "target": target,
        }

    def assert_common_baseline(self, target: Path) -> None:
        mise_source = (target / "mise.toml").read_text(encoding="utf-8")
        for task in ("format", "format-check", "lint", "check", "test", "build", "ci"):
            self.assertIn(f"[tasks.{task}]", mise_source)
        self.assertIn('zig = "0.16.0"', mise_source)
        self.assertIn('lefthook = "2.1.10"', mise_source)
        lock_source = (target / "mise.lock").read_text(encoding="utf-8")
        self.assertIn('version = "0.16.0"', lock_source)
        self.assertIn('version = "2.1.10"', lock_source)
        ci_order = [
            mise_source.index('{ task = "format-check" }'),
            mise_source.index('{ task = "lint" }'),
            mise_source.index('{ task = "check" }'),
            mise_source.index('{ task = "test" }'),
            mise_source.index('{ task = "build" }'),
        ]
        self.assertEqual(sorted(ci_order), ci_order)

        lefthook_source = (target / "lefthook.yml").read_text(encoding="utf-8")
        order = [
            lefthook_source.index("partial-stage-guard"),
            lefthook_source.index("format-staged-zig"),
            lefthook_source.index("lint-staged-zig"),
            lefthook_source.index("quick-project-check"),
        ]
        self.assertEqual(sorted(order), order)
        self.assertIn("stage_fixed: true", lefthook_source)
        self.assertNotIn("parallel: true", lefthook_source)
        self.assertNotIn("mise run test", lefthook_source)
        self.assertNotIn("mise run build", lefthook_source)
        self.assertTrue((target / ".git" / "hooks" / "pre-commit").is_file())
        hooks_path = subprocess.run(
            ["git", "-C", str(target), "config", "--local", "--get", "core.hooksPath"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.assertEqual(".git/hooks", hooks_path)

        workflow = (target / ".github" / "workflows" / "validate.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("ubuntu-latest", workflow)
        self.assertIn("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", workflow)
        self.assertIn("jdx/mise-action@3c2e0cf82a5b2e5249f0d3635a4d83d0ae861518", workflow)
        self.assertIn("version: 2026.8.5", workflow)
        self.assertIn("run: mise run ci", workflow)

        renovate = json.loads(
            (target / ".github" / "renovate.json").read_text(encoding="utf-8")
        )
        self.assertEqual(["config:recommended"], renovate["extends"])
        self.assertEqual("enabled", renovate["semanticCommits"])
        self.assertEqual(["dependencies"], renovate["labels"])
        self.assertNotIn("automerge", renovate)
        self.assertNotIn("lockFileMaintenance", renovate)

    def assert_command_order(self, commands: list[dict[str, object]]) -> None:
        argv = [entry["argv"] for entry in commands]
        self.assertEqual(
            [
                ["install"],
                ["exec", "--", "zig", "init"],
                ["exec", "--", "lefthook", "install", "--force"],
                ["run", "ci"],
            ],
            argv,
        )

    def assert_initializer_boundary(
        self,
        report: dict[str, object],
        target: Path,
    ) -> None:
        command = next(
            entry
            for entry in report["commands"]
            if entry["argv"][1:] == ["exec", "--", "zig", "init"]
        )
        initializer_target = Path(command["cwd"])
        self.assertEqual("sample_project", initializer_target.name)
        self.assertTrue(initializer_target.parent.name.startswith(".bootstrap-zig-init-"))
        self.assertEqual(
            {"MISE_TRUSTED_CONFIG_PATHS": str(target.resolve())},
            command["environment"],
        )
        self.assertFalse(initializer_target.parent.exists())

    def assert_repository_has_no_commit(self, target: Path) -> None:
        completed = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "--verify", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(0, completed.returncode)


if __name__ == "__main__":
    unittest.main()
