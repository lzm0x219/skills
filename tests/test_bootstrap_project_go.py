from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = (
    ROOT
    / "skills"
    / "development"
    / "workflows"
    / "bootstrap-project"
    / "scripts"
    / "bootstrap_go.py"
)
VERSIONS = {"go": "1.26.6", "lefthook": "2.1.10"}


class BootstrapProjectGoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.fake_mise = self.root / "fake-mise"
        self._write_fake_mise()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_new_library_uses_go_mod_init_and_complete_baseline(self) -> None:
        target = self.root / "sample-go-library"
        report = self._run(
            target,
            mode="new",
            shape="library",
            name="sample-go-library",
            module_path="example.com/sample-go-library",
        )

        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["shape"], "library")
        self.assertEqual(report["verification"]["no_commit"], "passed")
        self.assertIn("package sample_go_library", (target / "library.go").read_text())
        self.assertTrue((target / "library_test.go").is_file())
        self.assertFalse((target / "go.sum").exists())
        self._assert_common_baseline(target)
        self.assertIn(
            [
                str(self.fake_mise),
                "exec",
                "--",
                "go",
                "mod",
                "init",
                "example.com/sample-go-library",
            ],
            [entry["argv"] for entry in report["commands"]],
        )

    def test_new_cli_has_thin_command_and_tested_behavior(self) -> None:
        target = self.root / "sample-go-cli"
        report = self._run(
            target,
            mode="new",
            shape="cli",
            name="sample-go-cli",
            module_path="example.com/sample-go-cli",
        )

        self.assertEqual(report["status"], "completed")
        main = target / "cmd" / "sample-go-cli" / "main.go"
        self.assertIn('"example.com/sample-go-cli"', main.read_text())
        self.assertIn("sample_go_cli.Greeting()", main.read_text())
        self.assertIn("func Greeting() string", (target / "greeting.go").read_text())
        self.assertTrue((target / "greeting_test.go").is_file())
        self._assert_common_baseline(target)

    def test_existing_library_preserves_module_sources_tests_and_readme(self) -> None:
        target = self._existing_library()
        protected = [
            "go.mod",
            "library.go",
            "library_test.go",
            "README.md",
        ]
        before = {path: self._hash(target / path) for path in protected}

        report = self._run(target, mode="existing", shape="library")

        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["changes"]["modified"], [])
        self.assertEqual(report["verification"]["preserved_project_files"], "passed")
        self.assertNotIn("go.mod", report["changes"]["created"])
        self.assertNotIn("library.go", report["changes"]["created"])
        self.assertEqual(before, {path: self._hash(target / path) for path in protected})
        self._assert_common_baseline(target)

    def test_existing_cli_preserves_thin_command_and_tested_package(self) -> None:
        target = self._existing_cli()
        protected = [
            "go.mod",
            "greeting.go",
            "greeting_test.go",
            "cmd/existing-go-cli/main.go",
        ]
        before = {path: self._hash(target / path) for path in protected}

        report = self._run(target, mode="existing", shape="cli")

        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["shape"], "cli")
        self.assertEqual(report["changes"]["modified"], [])
        self.assertEqual(before, {path: self._hash(target / path) for path in protected})
        self._assert_common_baseline(target)

    def test_existing_go_workspace_is_blocked_without_writes(self) -> None:
        target = self._existing_library()
        (target / "go.work").write_text("go 1.26.6\n", encoding="utf-8")
        before = self._tree_hashes(target)

        completed, report = self._run_failure(target, mode="existing")

        self.assertIn("Go workspace", completed.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(before, self._tree_hashes(target))

    def test_nested_module_is_blocked_without_writes(self) -> None:
        target = self._existing_library()
        nested = target / "tools"
        nested.mkdir()
        (nested / "go.mod").write_text(
            "module example.com/sample/tools\n\ngo 1.26.6\n",
            encoding="utf-8",
        )
        before = self._tree_hashes(target)

        completed, report = self._run_failure(target, mode="existing")

        self.assertIn("nested Go modules", completed.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(before, self._tree_hashes(target))

    def test_conflicting_go_version_is_blocked(self) -> None:
        target = self._existing_library()

        completed, report = self._run_failure(
            target,
            mode="existing",
            go_version="1.25.0",
        )

        self.assertIn("Go version", completed.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["changes"], {"created": [], "modified": [], "deleted": []})

    def test_ci_failure_is_partial_with_exact_command(self) -> None:
        target = self.root / "failed-go"
        completed, report = self._run_failure(
            target,
            mode="new",
            shape="library",
            name="failed-go",
            module_path="example.com/failed-go",
            extra_environment={"FAKE_MISE_FAIL_CI": "1"},
        )

        self.assertIn("mise run ci", completed.stderr)
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["failed_command"], [str(self.fake_mise), "run", "ci"])
        self.assertEqual(report["verification"]["mise_run_ci"], "failed")
        self.assertTrue((target / "go.mod").is_file())

    def test_existing_project_without_tests_is_blocked(self) -> None:
        target = self._existing_library()
        (target / "library_test.go").unlink()
        before = self._tree_hashes(target)

        completed, report = self._run_failure(target, mode="existing")

        self.assertIn("requires source files and tests", completed.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(before, self._tree_hashes(target))

    def test_new_project_name_cannot_be_a_go_keyword(self) -> None:
        target = self.root / "keyword"

        completed, report = self._run_failure(
            target,
            mode="new",
            shape="library",
            name="type",
            module_path="example.com/type",
        )

        self.assertIn("cannot form a Go package name", completed.stderr)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(target.exists())

    def _run(
        self,
        target: Path,
        *,
        mode: str,
        shape: str | None = None,
        name: str | None = None,
        module_path: str | None = None,
        go_version: str = VERSIONS["go"],
    ) -> dict[str, object]:
        completed, report = self._invoke(
            target,
            mode=mode,
            shape=shape,
            name=name,
            module_path=module_path,
            go_version=go_version,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return report

    def _run_failure(
        self,
        target: Path,
        *,
        mode: str,
        shape: str | None = None,
        name: str | None = None,
        module_path: str | None = None,
        go_version: str = VERSIONS["go"],
        extra_environment: dict[str, str] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        completed, report = self._invoke(
            target,
            mode=mode,
            shape=shape,
            name=name,
            module_path=module_path,
            go_version=go_version,
            extra_environment=extra_environment,
        )
        self.assertNotEqual(completed.returncode, 0)
        return completed, report

    def _invoke(
        self,
        target: Path,
        *,
        mode: str,
        shape: str | None,
        name: str | None,
        module_path: str | None,
        go_version: str,
        extra_environment: dict[str, str] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        report_path = self.root / f"report-{len(list(self.root.glob('report-*.json')))}.json"
        command = [
            sys.executable,
            str(ADAPTER),
            "--target",
            str(target),
            "--mode",
            mode,
            "--go-version",
            go_version,
            "--lefthook-version",
            VERSIONS["lefthook"],
            "--mise",
            str(self.fake_mise),
            "--report",
            str(report_path),
        ]
        if shape is not None:
            command.extend(["--shape", shape])
        if name is not None:
            command.extend(["--name", name])
        if module_path is not None:
            command.extend(["--module-path", module_path])
        environment = dict(**__import__("os").environ)
        if extra_environment:
            environment.update(extra_environment)
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )
        return completed, json.loads(report_path.read_text(encoding="utf-8"))

    def _existing_library(self) -> Path:
        target = self.root / "existing-go-library"
        target.mkdir()
        subprocess.run(["git", "init", "-q", str(target)], check=True)
        (target / "go.mod").write_text(
            "module example.com/existing-go-library\n\ngo 1.26.6\n",
            encoding="utf-8",
        )
        (target / "library.go").write_text(
            "package existing_go_library\n\nfunc Value() int { return 42 }\n",
            encoding="utf-8",
        )
        (target / "library_test.go").write_text(
            textwrap.dedent(
                """\
                package existing_go_library

                import "testing"

                func TestValue(t *testing.T) {
                    if Value() != 42 {
                        t.Fatal("unexpected value")
                    }
                }
                """
            ),
            encoding="utf-8",
        )
        (target / "README.md").write_text("# Existing Go library\n", encoding="utf-8")
        return target

    def _existing_cli(self) -> Path:
        target = self.root / "existing-go-cli"
        command = target / "cmd" / "existing-go-cli"
        command.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(target)], check=True)
        (target / "go.mod").write_text(
            "module example.com/existing-go-cli\n\ngo 1.26.6\n",
            encoding="utf-8",
        )
        (target / "greeting.go").write_text(
            'package existing_go_cli\n\nfunc Greeting() string { return "hello" }\n',
            encoding="utf-8",
        )
        (target / "greeting_test.go").write_text(
            textwrap.dedent(
                """\
                package existing_go_cli

                import "testing"

                func TestGreeting(t *testing.T) {
                    if Greeting() != "hello" {
                        t.Fatal("unexpected greeting")
                    }
                }
                """
            ),
            encoding="utf-8",
        )
        (command / "main.go").write_text(
            textwrap.dedent(
                """\
                package main

                import (
                    "fmt"

                    "example.com/existing-go-cli"
                )

                func main() {
                    fmt.Println(existing_go_cli.Greeting())
                }
                """
            ),
            encoding="utf-8",
        )
        return target

    def _assert_common_baseline(self, target: Path) -> None:
        mise = (target / "mise.toml").read_text(encoding="utf-8")
        self.assertIn('go = "1.26.6"', mise)
        self.assertIn('lefthook = "2.1.10"', mise)
        for task in (
            "install",
            "format",
            "format-check",
            "modules-check",
            "lint",
            "test",
            "build",
            "ci",
        ):
            self.assertIn(f"[tasks.{task}]", mise)
        self.assertIn("go mod tidy -diff", mise)
        self.assertIn("go vet -mod=readonly ./...", mise)
        self.assertIn("go test -mod=readonly -count=1 ./...", mise)
        self.assertIn("go build -mod=readonly ./...", mise)

        lefthook = (target / "lefthook.yml").read_text(encoding="utf-8")
        self.assertIn("piped: true", lefthook)
        self.assertLess(lefthook.index("partial-stage-guard"), lefthook.index("format-staged-go"))
        self.assertNotIn("mise run test", lefthook)
        self.assertNotIn("mise run build", lefthook)
        hook = (target / ".git" / "hooks" / "pre-commit").read_text(encoding="utf-8")
        self.assertIn('--no-stage-fixed "$@"', hook)

        workflow = (target / ".github" / "workflows" / "validate.yml").read_text()
        self.assertEqual(workflow.count("mise run ci"), 1)
        self.assertIn("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", workflow)
        renovate = json.loads((target / ".github" / "renovate.json").read_text())
        self.assertEqual(renovate["lockFileMaintenance"], {"enabled": False})

    def _write_fake_mise(self) -> None:
        source = textwrap.dedent(
            f"""\
            #!{sys.executable}
            from pathlib import Path
            import os
            import sys

            args = sys.argv[1:]
            cwd = Path.cwd()
            if args == ["install"]:
                (cwd / "mise.lock").write_text(
                    '[[tools.go]]\\nversion = "{VERSIONS["go"]}"\\n\\n'
                    '[[tools.lefthook]]\\nversion = "{VERSIONS["lefthook"]}"\\n',
                    encoding="utf-8",
                )
                raise SystemExit(0)
            if args[:3] == ["exec", "--", "go"]:
                go_args = args[3:]
                if go_args[:2] == ["mod", "init"]:
                    (cwd / "go.mod").write_text(
                        f'module {{go_args[2]}}\\n\\ngo {VERSIONS["go"]}\\n',
                        encoding="utf-8",
                    )
                    raise SystemExit(0)
                if go_args[:2] == ["mod", "tidy"]:
                    raise SystemExit(0)
                if go_args == ["run", ".lefthook/install_go.go"]:
                    hook = cwd / ".git" / "hooks" / "pre-commit"
                    hook.parent.mkdir(parents=True, exist_ok=True)
                    hook.write_text(
                        '#!/bin/sh\\ncall_lefthook run "pre-commit" --no-stage-fixed "$@"\\n',
                        encoding="utf-8",
                    )
                    hook.chmod(0o755)
                    raise SystemExit(0)
            if args == ["run", "ci"]:
                if os.environ.get("FAKE_MISE_FAIL_CI"):
                    print("simulated CI failure", file=sys.stderr)
                    raise SystemExit(1)
                raise SystemExit(0)
            print(f"unsupported fake mise command: {{args!r}}", file=sys.stderr)
            raise SystemExit(2)
            """
        )
        self.fake_mise.write_text(source, encoding="utf-8")
        self.fake_mise.chmod(0o755)

    @staticmethod
    def _hash(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _tree_hashes(target: Path) -> dict[str, str]:
        return {
            path.relative_to(target).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(target.rglob("*"))
            if path.is_file() and ".git" not in path.relative_to(target).parts
        }


if __name__ == "__main__":
    unittest.main()
