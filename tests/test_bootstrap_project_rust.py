#!/usr/bin/env python3

from __future__ import annotations

import hashlib
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
    / "bootstrap_rust.py"
)


class BootstrapRustTest(unittest.TestCase):
    def test_creates_a_library_with_real_quality_tasks(self) -> None:
        result = self.invoke_new("library", "sample_library")

        self.assertEqual(0, result["completed"].returncode, result["completed"].stderr)
        target = result["target"]
        source = (target / "src" / "lib.rs").read_text(encoding="utf-8")
        self.assertIn("#[cfg(test)]", source)
        self.assertIn("add_returns_the_sum_of_both_operands", source)
        self.assert_common_baseline(target)
        self.assertEqual("completed", result["report"]["status"])
        self.assertEqual("passed", result["report"]["verification"]["no_commit"])

    def test_creates_a_cli_with_a_thin_main_and_testable_library(self) -> None:
        result = self.invoke_new("cli", "sample-cli")

        self.assertEqual(0, result["completed"].returncode, result["completed"].stderr)
        target = result["target"]
        self.assertIn(
            'println!("{}", sample_cli::message());',
            (target / "src" / "main.rs").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "message_returns_the_cli_greeting",
            (target / "src" / "lib.rs").read_text(encoding="utf-8"),
        )
        self.assert_common_baseline(target)

    def test_existing_library_preserves_cargo_source_and_readme(self) -> None:
        result = self.invoke_existing()

        self.assertEqual(0, result["completed"].returncode, result["completed"].stderr)
        target = result["target"]
        self.assertEqual(result["before"], self.preserved_hashes(target))
        self.assertEqual("completed", result["report"]["status"])
        self.assertEqual("passed", result["report"]["verification"]["preserved_project_files"])
        self.assertIn("mise.toml", result["report"]["changes"]["created"])
        self.assertIn("Cargo.lock", result["report"]["changes"]["created"])
        self.assert_common_baseline(target)

    def test_existing_project_blocks_alternative_manager_before_writes(self) -> None:
        result = self.invoke_existing(alternative=True)

        self.assertNotEqual(0, result["completed"].returncode)
        self.assertEqual("blocked", result["report"]["status"])
        self.assertIn(".tool-versions", result["report"]["error"])
        self.assertEqual([], result["commands"])
        self.assertEqual(result["before"], self.preserved_hashes(result["target"]))
        self.assertFalse((result["target"] / "mise.toml").exists())

    def test_existing_project_blocks_conflicting_toolchain_version(self) -> None:
        result = self.invoke_existing(toolchain_version="1.96.1")

        self.assertNotEqual(0, result["completed"].returncode)
        self.assertEqual("blocked", result["report"]["status"])
        self.assertIn("rust-toolchain.toml", result["report"]["error"])
        self.assertEqual([], result["commands"])
        self.assertFalse((result["target"] / "mise.toml").exists())

    def test_ci_failure_is_partial_and_names_the_failed_command(self) -> None:
        result = self.invoke_new("library", "sample_library", fail_on="run ci")

        self.assertNotEqual(0, result["completed"].returncode)
        report = result["report"]
        self.assertEqual("partial", report["status"])
        self.assertEqual([str(result["fake_mise"]), "run", "ci"], report["failed_command"])
        self.assertEqual("failed", report["verification"]["mise_run_ci"])
        self.assertEqual(
            {"rust": "1.97.1", "lefthook": "2.1.10"},
            report["versions"],
        )
        self.assertTrue(report["changes"]["created"])

    def invoke_new(
        self,
        shape: str,
        name: str,
        *,
        fail_on: str = "",
    ) -> dict[str, object]:
        root, fake_mise, environment = self.setup_fake(fail_on)
        target = root / "project"
        report = root / "report.json"
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--target",
                str(target),
                "--mode",
                "new",
                "--shape",
                shape,
                "--name",
                name,
                "--rust-version",
                "1.97.1",
                "--lefthook-version",
                "2.1.10",
                "--mise",
                str(fake_mise),
                "--report",
                str(report),
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        return self.result(root, target, report, completed, fake_mise)

    def invoke_existing(
        self,
        *,
        alternative: bool = False,
        toolchain_version: str | None = None,
    ) -> dict[str, object]:
        root, fake_mise, environment = self.setup_fake("")
        target = root / "project"
        (target / "src").mkdir(parents=True)
        (target / "Cargo.toml").write_text(
            textwrap.dedent(
                """\
                [package]
                name = "existing_library"
                version = "0.1.0"
                edition = "2024"
                rust-version = "1.97.1"

                [dependencies]
                """
            ),
            encoding="utf-8",
        )
        (target / "src" / "lib.rs").write_text(
            "pub const fn answer() -> u8 { 42 }\n",
            encoding="utf-8",
        )
        (target / "README.md").write_text("# Existing\n", encoding="utf-8")
        if alternative:
            (target / ".tool-versions").write_text("rust 1.97.1\n", encoding="utf-8")
        if toolchain_version:
            (target / "rust-toolchain.toml").write_text(
                f'[toolchain]\nchannel = "{toolchain_version}"\n',
                encoding="utf-8",
            )
        subprocess.run(
            ["git", "-C", str(target), "init"],
            check=True,
            capture_output=True,
            text=True,
        )
        before = self.preserved_hashes(target)
        report = root / "report.json"
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--target",
                str(target),
                "--mode",
                "existing",
                "--shape",
                "library",
                "--lefthook-version",
                "2.1.10",
                "--mise",
                str(fake_mise),
                "--report",
                str(report),
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        result = self.result(root, target, report, completed, fake_mise)
        result["before"] = before
        return result

    def setup_fake(self, fail_on: str) -> tuple[Path, Path, dict[str, str]]:
        temporary = tempfile.TemporaryDirectory(prefix="bootstrap-rust-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        log = root / "commands.jsonl"
        fake = root / "fake_mise.py"
        fake.write_text(
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
                    raise SystemExit(7)
                if args == ["install"]:
                    (cwd / "mise.lock").write_text(
                        '[[tools.lefthook]]\\nversion = "2.1.10"\\n\\n'
                        '[[tools.rust]]\\nversion = "1.97.1"\\n',
                        encoding="utf-8",
                    )
                elif len(args) > 4 and args[:4] == ["exec", "--", "cargo", "init"]:
                    shape = "lib.rs" if "--lib" in args else "main.rs"
                    (cwd / "src").mkdir(exist_ok=True)
                    (cwd / "Cargo.toml").write_text(
                        '[package]\\nname = "official"\\nversion = "0.1.0"\\n'
                        'edition = "2024"\\n\\n[dependencies]\\n',
                        encoding="utf-8",
                    )
                    (cwd / "src" / shape).write_text("official\\n", encoding="utf-8")
                elif args == ["exec", "--", "cargo", "generate-lockfile"]:
                    (cwd / "Cargo.lock").write_text(
                        "version = 4\\n\\n[[package]]\\nname = \\"fixture\\"\\nversion = \\"0.1.0\\"\\n",
                        encoding="utf-8",
                    )
                elif args == ["exec", "--", "sh", ".lefthook/install-hooks.sh"]:
                    hook = cwd / ".git" / "hooks" / "pre-commit"
                    hook.parent.mkdir(parents=True, exist_ok=True)
                    hook.write_text(
                        '#!/bin/sh\\nexport MISE_TRUSTED_CONFIG_PATHS="$(git rev-parse '
                        '--show-toplevel)"; call_lefthook run "pre-commit" '
                        '--no-stage-fixed "$@"\\n',
                        encoding="utf-8",
                    )
                    hook.chmod(0o755)
                elif args == ["run", "ci"]:
                    if not (cwd / "Cargo.lock").is_file():
                        raise SystemExit(8)
                """
            ),
            encoding="utf-8",
        )
        fake.chmod(0o755)
        environment = os.environ.copy()
        environment.update(
            {
                "FAKE_MISE_FAIL_ON": fail_on,
                "FAKE_MISE_LOG": str(log),
            }
        )
        return root, fake, environment

    def result(
        self,
        root: Path,
        target: Path,
        report: Path,
        completed: subprocess.CompletedProcess[str],
        fake_mise: Path,
    ) -> dict[str, object]:
        log = root / "commands.jsonl"
        commands = (
            [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
            if log.is_file()
            else []
        )
        return {
            "commands": commands,
            "completed": completed,
            "fake_mise": fake_mise,
            "report": json.loads(report.read_text(encoding="utf-8")),
            "target": target,
        }

    def assert_common_baseline(self, target: Path) -> None:
        mise = (target / "mise.toml").read_text(encoding="utf-8")
        for task in ("format", "format-check", "lint", "check", "test", "build", "ci"):
            self.assertIn(f"[tasks.{task}]", mise)
        self.assertIn('rust = "1.97.1"', mise)
        lefthook = (target / "lefthook.yml").read_text(encoding="utf-8")
        order = [
            lefthook.index("partial-stage-guard"),
            lefthook.index("format-staged-rust"),
            lefthook.index("lint-project-rust"),
            lefthook.index("quick-project-check"),
        ]
        self.assertEqual(sorted(order), order)
        self.assertIn("piped: true", lefthook)
        self.assertNotIn("stage_fixed", lefthook)
        self.assertNotIn("{staged_files}", lefthook)
        self.assertNotIn("cargo test", lefthook)
        self.assertNotIn("cargo build", lefthook)
        hook = (target / ".git" / "hooks" / "pre-commit").read_text(
            encoding="utf-8"
        )
        self.assertIn('--no-stage-fixed "$@"', hook)
        self.assertIn("MISE_TRUSTED_CONFIG_PATHS", hook)
        staged_formatter = (
            target / ".lefthook" / "format-staged-rust.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("git diff --cached", staged_formatter)
        self.assertIn("-z -- '*.rs'", staged_formatter)
        self.assertIn("xargs -0 git add --", staged_formatter)
        renovate = json.loads(
            (target / ".github" / "renovate.json").read_text(encoding="utf-8")
        )
        self.assertEqual({"enabled": False}, renovate["lockFileMaintenance"])

    def preserved_hashes(self, target: Path) -> dict[str, str]:
        return {
            path: hashlib.sha256((target / path).read_bytes()).hexdigest()
            for path in ("Cargo.toml", "README.md", "src/lib.rs")
        }


if __name__ == "__main__":
    unittest.main()
