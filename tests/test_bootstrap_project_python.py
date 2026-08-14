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
    / "bootstrap_python.py"
)
VERSIONS = {
    "python": "3.14.7",
    "uv": "0.12.4",
    "uv_build": "0.12.4",
    "build": "1.5.0",
    "mypy": "2.3.0",
    "pytest": "9.1.1",
    "ruff": "0.16.3",
    "lefthook": "2.1.10",
}


class BootstrapPythonTest(unittest.TestCase):
    def test_creates_a_library_with_pytest_and_typed_package(self) -> None:
        result = self.invoke_new("library", "sample-library")

        self.assertEqual(0, result["completed"].returncode, result["completed"].stderr)
        target = result["target"]
        source = (target / "src" / "sample_library" / "__init__.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("def add(left: int, right: int) -> int", source)
        self.assertTrue((target / "src" / "sample_library" / "py.typed").is_file())
        self.assertIn(
            "test_add_returns_the_sum_of_both_operands",
            (target / "tests" / "test_package.py").read_text(encoding="utf-8"),
        )
        self.assert_common_baseline(target)
        self.assertEqual("completed", result["report"]["status"])
        self.assertEqual("passed", result["report"]["verification"]["no_commit"])

    def test_creates_a_cli_with_a_thin_entry_and_tested_core(self) -> None:
        result = self.invoke_new("cli", "sample-cli")

        self.assertEqual(0, result["completed"].returncode, result["completed"].stderr)
        target = result["target"]
        entry = (target / "src" / "sample_cli" / "cli.py").read_text(encoding="utf-8")
        self.assertIn("from .core import message", entry)
        self.assertIn("print(message())", entry)
        core = (target / "src" / "sample_cli" / "core.py").read_text(encoding="utf-8")
        self.assertIn("def message() -> str", core)
        pyproject = (target / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('sample-cli = "sample_cli.cli:main"', pyproject)
        self.assert_common_baseline(target)

    def test_existing_library_preserves_package_metadata_and_layout(self) -> None:
        result = self.invoke_existing()

        self.assertEqual(0, result["completed"].returncode, result["completed"].stderr)
        target = result["target"]
        self.assertEqual(result["before"], self.preserved_hashes(target))
        self.assertEqual("completed", result["report"]["status"])
        self.assertEqual(
            "passed",
            result["report"]["verification"]["preserved_project_files"],
        )
        self.assertIn("mise.toml", result["report"]["changes"]["created"])
        self.assertNotIn("pyproject.toml", result["report"]["changes"]["modified"])
        self.assert_common_baseline(target)

    def test_existing_project_blocks_an_alternative_manager_before_writes(self) -> None:
        result = self.invoke_existing(alternative=True)

        self.assertNotEqual(0, result["completed"].returncode)
        self.assertEqual("blocked", result["report"]["status"])
        self.assertIn("poetry.lock", result["report"]["error"])
        self.assertEqual([], result["commands"])
        self.assertEqual(result["before"], self.preserved_hashes(result["target"]))
        self.assertFalse((result["target"] / "mise.toml").exists())

    def test_existing_project_blocks_a_conflicting_uv_build_version(self) -> None:
        result = self.invoke_existing(requested_uv="0.12.3")

        self.assertNotEqual(0, result["completed"].returncode)
        self.assertEqual("blocked", result["report"]["status"])
        self.assertIn("uv_build", result["report"]["error"])
        self.assertEqual([], result["commands"])
        self.assertFalse((result["target"] / "mise.toml").exists())

    def test_ci_failure_is_partial_and_names_the_failed_command(self) -> None:
        result = self.invoke_new("library", "sample-library", fail_on="run ci")

        self.assertNotEqual(0, result["completed"].returncode)
        report = result["report"]
        self.assertEqual("partial", report["status"])
        self.assertEqual([str(result["fake_mise"]), "run", "ci"], report["failed_command"])
        self.assertEqual("failed", report["verification"]["mise_run_ci"])
        self.assertEqual(VERSIONS, report["versions"])
        self.assertTrue(report["changes"]["created"])

    def test_existing_project_requires_a_current_uv_lock(self) -> None:
        result = self.invoke_existing(missing_lock=True)

        self.assertNotEqual(0, result["completed"].returncode)
        self.assertEqual("blocked", result["report"]["status"])
        self.assertIn("uv.lock", result["report"]["error"])
        self.assertEqual([], result["commands"])

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
            self.command(target, report, fake_mise)
            + ["--mode", "new", "--shape", shape, "--name", name],
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
        requested_uv: str = "0.12.4",
        missing_lock: bool = False,
    ) -> dict[str, object]:
        root, fake_mise, environment = self.setup_fake("")
        target = root / "project"
        package = target / "src" / "existing_library"
        package.mkdir(parents=True)
        (target / "tests").mkdir()
        (target / "pyproject.toml").write_text(
            textwrap.dedent(
                """\
                [project]
                name = "existing-library"
                version = "0.4.0"
                readme = "README.md"
                requires-python = ">=3.14.7"
                dependencies = []

                [dependency-groups]
                dev = [
                    "build==1.5.0",
                    "mypy==2.3.0",
                    "pytest==9.1.1",
                    "ruff==0.16.3",
                ]

                [build-system]
                requires = ["uv_build==0.12.4"]
                build-backend = "uv_build"

                [tool.ruff]
                target-version = "py314"

                [tool.mypy]
                python_version = "3.14"
                strict = true

                [tool.pytest.ini_options]
                testpaths = ["tests"]
                """
            ),
            encoding="utf-8",
        )
        (target / ".python-version").write_text("3.14.7\n", encoding="utf-8")
        (package / "__init__.py").write_text(
            "def answer() -> int:\n    return 42\n",
            encoding="utf-8",
        )
        (target / "tests" / "test_answer.py").write_text(
            textwrap.dedent(
                """\
                from existing_library import answer


                def test_answer_returns_42() -> None:
                    assert answer() == 42
                """
            ),
            encoding="utf-8",
        )
        (target / "README.md").write_text("# Existing\n", encoding="utf-8")
        if not missing_lock:
            (target / "uv.lock").write_text(
                'version = 1\nrevision = 3\nrequires-python = ">=3.14.7"\n',
                encoding="utf-8",
            )
        if alternative:
            (target / "poetry.lock").write_text("# alternative\n", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(target), "init"],
            check=True,
            capture_output=True,
            text=True,
        )
        before = self.preserved_hashes(target)
        report = root / "report.json"
        completed = subprocess.run(
            self.command(target, report, fake_mise, uv=requested_uv)
            + ["--mode", "existing", "--shape", "library"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        result = self.result(root, target, report, completed, fake_mise)
        result["before"] = before
        return result

    def command(
        self,
        target: Path,
        report: Path,
        fake_mise: Path,
        *,
        uv: str = "0.12.4",
    ) -> list[str]:
        return [
            sys.executable,
            str(SCRIPT),
            "--target",
            str(target),
            "--python-version",
            "3.14.7",
            "--uv-version",
            uv,
            "--build-version",
            "1.5.0",
            "--mypy-version",
            "2.3.0",
            "--pytest-version",
            "9.1.1",
            "--ruff-version",
            "0.16.3",
            "--lefthook-version",
            "2.1.10",
            "--mise",
            str(fake_mise),
            "--report",
            str(report),
        ]

    def setup_fake(self, fail_on: str) -> tuple[Path, Path, dict[str, str]]:
        temporary = tempfile.TemporaryDirectory(prefix="bootstrap-python-")
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
                        '[[tools.python]]\\nversion = "3.14.7"\\n\\n'
                        '[[tools.uv]]\\nversion = "0.12.4"\\n',
                        encoding="utf-8",
                    )
                elif len(args) > 4 and args[:4] == ["exec", "--", "uv", "init"]:
                    name = args[args.index("--name") + 1]
                    module = name.replace("-", "_").replace(".", "_")
                    package = cwd / "src" / module
                    package.mkdir(parents=True)
                    (cwd / ".python-version").write_text("3.14.7\\n", encoding="utf-8")
                    (cwd / "pyproject.toml").write_text("[project]\\n", encoding="utf-8")
                    (package / "__init__.py").write_text("official\\n", encoding="utf-8")
                    if "--lib" in args:
                        (package / "py.typed").touch()
                elif args == ["exec", "--", "uv", "lock"]:
                    (cwd / "uv.lock").write_text(
                        'version = 1\\nrevision = 3\\nrequires-python = ">=3.14.7"\\n',
                        encoding="utf-8",
                    )
                elif args == ["exec", "--", "uv", "lock", "--check"]:
                    if not (cwd / "uv.lock").is_file():
                        raise SystemExit(8)
                elif args == ["exec", "--", "uv", "sync", "--locked", "--all-groups"]:
                    if not (cwd / "uv.lock").is_file():
                        raise SystemExit(9)
                elif args == ["exec", "--", "python", ".lefthook/install_python.py"]:
                    hook = cwd / ".git" / "hooks" / "pre-commit"
                    hook.parent.mkdir(parents=True, exist_ok=True)
                    hook.write_text(
                        'LEFTHOOK installed\\ncall_lefthook run "pre-commit" '
                        '--no-stage-fixed "$@"\\n',
                        encoding="utf-8",
                    )
                    hook.chmod(0o755)
                elif args == ["run", "ci"]:
                    if not (cwd / "uv.lock").is_file():
                        raise SystemExit(10)
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
        for task in (
            "install",
            "format",
            "format-check",
            "lint",
            "check",
            "test",
            "build",
            "ci",
        ):
            self.assertIn(f"[tasks.{task}]", mise)
        self.assertIn('python = "3.14.7"', mise)
        self.assertIn('uv = "0.12.4"', mise)
        self.assertIn("uv run --locked", mise)
        lefthook = (target / "lefthook.yml").read_text(encoding="utf-8")
        self.assertIn("piped: true", lefthook)
        order = [
            lefthook.index("partial-stage-guard"),
            lefthook.index("format-staged-python"),
            lefthook.index("lint-project-python"),
            lefthook.index("type-check-project"),
        ]
        self.assertEqual(sorted(order), order)
        self.assertNotIn("pytest", lefthook)
        self.assertNotIn("python -m build", lefthook)
        renovate = (target / ".github" / "renovate.json").read_text(encoding="utf-8")
        self.assertIn('"lockFileMaintenance"', renovate)
        self.assertIn('"enabled": false', renovate)
        self.assertTrue((target / "uv.lock").is_file())

    def preserved_hashes(self, target: Path) -> dict[str, str]:
        paths = (
            ".python-version",
            "README.md",
            "pyproject.toml",
            "src/existing_library/__init__.py",
            "tests/test_answer.py",
        )
        return {
            path: hashlib.sha256((target / path).read_bytes()).hexdigest()
            for path in paths
        }


if __name__ == "__main__":
    unittest.main()
