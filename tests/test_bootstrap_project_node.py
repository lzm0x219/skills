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
    / "bootstrap_node.py"
)
VERSIONS = {
    "node": "24.19.0",
    "pnpm": "11.21.0",
    "typescript": "7.0.2",
    "node_types": "24.13.3",
    "oxfmt": "0.63.0",
    "oxlint": "1.78.0",
    "vitest": "4.1.10",
    "lefthook": "2.1.10",
}


class BootstrapNodeTest(unittest.TestCase):
    def test_creates_an_esm_library_with_vitest_and_oxc(self) -> None:
        result = self.invoke_new("library", "sample-library")

        self.assertEqual(0, result["completed"].returncode, result["completed"].stderr)
        target = result["target"]
        package = json.loads((target / "package.json").read_text(encoding="utf-8"))
        self.assertEqual("module", package["type"])
        self.assertIn("exports", package)
        self.assertEqual("vitest run", package["scripts"]["test"])
        self.assertIn("returns a greeting", (target / "test" / "index.test.ts").read_text())
        self.assert_common_baseline(target)
        self.assertEqual("completed", result["report"]["status"])
        self.assertEqual("passed", result["report"]["verification"]["no_commit"])

    def test_creates_a_cli_with_a_thin_entry_and_tested_library(self) -> None:
        result = self.invoke_new("cli", "sample-cli")

        self.assertEqual(0, result["completed"].returncode, result["completed"].stderr)
        target = result["target"]
        entry = (target / "src" / "cli.ts").read_text(encoding="utf-8")
        self.assertTrue(entry.startswith("#!/usr/bin/env node"))
        self.assertIn('import { message } from "./index.js";', entry)
        self.assertIn("returns the CLI greeting", (target / "test" / "index.test.ts").read_text())
        package = json.loads((target / "package.json").read_text(encoding="utf-8"))
        self.assertEqual({"sample-cli": "./dist/cli.js"}, package["bin"])
        self.assert_common_baseline(target)

    def test_existing_library_preserves_sources_scripts_and_compatible_configs(self) -> None:
        result = self.invoke_existing()

        self.assertEqual(0, result["completed"].returncode, result["completed"].stderr)
        target = result["target"]
        self.assertEqual(result["before"], self.preserved_hashes(target))
        package = json.loads((target / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(result["scripts"], package["scripts"])
        self.assertEqual("completed", result["report"]["status"])
        self.assertEqual(
            "passed",
            result["report"]["verification"]["preserved_project_files"],
        )
        self.assertIn("mise.toml", result["report"]["changes"]["created"])
        self.assertIn("pnpm-lock.yaml", result["report"]["changes"]["created"])
        self.assert_common_baseline(target)

    def test_existing_project_blocks_an_alternative_manager_before_writes(self) -> None:
        result = self.invoke_existing(alternative=True)

        self.assertNotEqual(0, result["completed"].returncode)
        self.assertEqual("blocked", result["report"]["status"])
        self.assertIn("package-lock.json", result["report"]["error"])
        self.assertEqual([], result["commands"])
        self.assertEqual(result["before"], self.preserved_hashes(result["target"]))
        self.assertFalse((result["target"] / "mise.toml").exists())

    def test_existing_project_blocks_a_conflicting_pnpm_version(self) -> None:
        result = self.invoke_existing(requested_pnpm="11.20.0")

        self.assertNotEqual(0, result["completed"].returncode)
        self.assertEqual("blocked", result["report"]["status"])
        self.assertIn("pnpm", result["report"]["error"])
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

    def test_generated_package_excludes_rejected_tooling(self) -> None:
        result = self.invoke_new("library", "sample-library")

        self.assertEqual(0, result["completed"].returncode, result["completed"].stderr)
        target = result["target"]
        package_source = (target / "package.json").read_text(encoding="utf-8")
        combined = package_source + (target / "lefthook.yml").read_text(encoding="utf-8")
        for forbidden in ("prettier", "eslint", "typescript-eslint", "node:test"):
            self.assertNotIn(forbidden, combined.lower())

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
        requested_pnpm: str = "11.21.0",
    ) -> dict[str, object]:
        root, fake_mise, environment = self.setup_fake("")
        target = root / "project"
        (target / "src").mkdir(parents=True)
        (target / "test").mkdir()
        scripts = {
            "custom": "node ./scripts/custom.mjs",
            "test": "vitest run",
        }
        package = {
            "name": "existing-library",
            "version": "0.4.0",
            "private": True,
            "type": "module",
            "engines": {"node": "24.19.0", "pnpm": "11.21.0"},
            "packageManager": "pnpm@11.21.0",
            "exports": {
                ".": {"types": "./dist/index.d.ts", "import": "./dist/index.js"}
            },
            "scripts": scripts,
            "devDependencies": {
                "@types/node": "24.13.3",
                "oxfmt": "0.63.0",
                "oxlint": "1.78.0",
                "typescript": "7.0.2",
                "vitest": "4.1.10",
            },
        }
        (target / "package.json").write_text(
            json.dumps(package, indent=2) + "\n",
            encoding="utf-8",
        )
        (target / "src" / "index.ts").write_text(
            "export const answer = (): number => 42;\n",
            encoding="utf-8",
        )
        (target / "test" / "index.test.ts").write_text(
            textwrap.dedent(
                """\
                import { expect, test } from "vitest";
                import { answer } from "../src/index.js";

                test("returns the existing answer", () => {
                  expect(answer()).toBe(42);
                });
                """
            ),
            encoding="utf-8",
        )
        (target / "README.md").write_text("# Existing\n", encoding="utf-8")
        (target / "tsconfig.json").write_text(
            json.dumps(
                {
                    "compilerOptions": {
                        "module": "NodeNext",
                        "moduleResolution": "NodeNext",
                        "noEmit": True,
                        "strict": True,
                    },
                    "include": ["src/**/*.ts", "test/**/*.ts"],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (target / "vitest.config.ts").write_text(
            'import { defineConfig } from "vitest/config";\n'
            "export default defineConfig({ test: { environment: \"node\" } });\n",
            encoding="utf-8",
        )
        if alternative:
            (target / "package-lock.json").write_text("{}\n", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(target), "init"],
            check=True,
            capture_output=True,
            text=True,
        )
        before = self.preserved_hashes(target)
        report = root / "report.json"
        completed = subprocess.run(
            self.command(target, report, fake_mise, pnpm=requested_pnpm)
            + ["--mode", "existing", "--shape", "library"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        result = self.result(root, target, report, completed, fake_mise)
        result["before"] = before
        result["scripts"] = scripts
        return result

    def command(
        self,
        target: Path,
        report: Path,
        fake_mise: Path,
        *,
        pnpm: str = "11.21.0",
    ) -> list[str]:
        return [
            sys.executable,
            str(SCRIPT),
            "--target",
            str(target),
            "--node-version",
            "24.19.0",
            "--pnpm-version",
            pnpm,
            "--typescript-version",
            "7.0.2",
            "--node-types-version",
            "24.13.3",
            "--oxfmt-version",
            "0.63.0",
            "--oxlint-version",
            "1.78.0",
            "--vitest-version",
            "4.1.10",
            "--lefthook-version",
            "2.1.10",
            "--mise",
            str(fake_mise),
            "--report",
            str(report),
        ]

    def setup_fake(self, fail_on: str) -> tuple[Path, Path, dict[str, str]]:
        temporary = tempfile.TemporaryDirectory(prefix="bootstrap-node-")
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
                        '[[tools.node]]\\nversion = "24.19.0"\\n\\n'
                        '[[tools.pnpm]]\\nversion = "11.21.0"\\n',
                        encoding="utf-8",
                    )
                elif args == ["exec", "--", "pnpm", "install", "--lockfile-only"]:
                    (cwd / "pnpm-lock.yaml").write_text(
                        "lockfileVersion: '9.0'\\n",
                        encoding="utf-8",
                    )
                elif args == ["exec", "--", "pnpm", "install", "--frozen-lockfile"]:
                    if not (cwd / "pnpm-lock.yaml").is_file():
                        raise SystemExit(8)
                elif args == ["exec", "--", "node", ".lefthook/install-node.mjs"]:
                    hook = cwd / ".git" / "hooks" / "pre-commit"
                    hook.parent.mkdir(parents=True, exist_ok=True)
                    hook.write_text(
                        'LEFTHOOK installed\\ncall_lefthook run "pre-commit" '
                        '--no-stage-fixed "$@"\\n',
                        encoding="utf-8",
                    )
                    hook.chmod(0o755)
                elif args == ["run", "ci"]:
                    if not (cwd / "pnpm-lock.yaml").is_file():
                        raise SystemExit(9)
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
        self.assertIn('node = "24.19.0"', mise)
        self.assertIn('pnpm = "11.21.0"', mise)
        lefthook = (target / "lefthook.yml").read_text(encoding="utf-8")
        self.assertIn("piped: true", lefthook)
        order = [
            lefthook.index("partial-stage-guard"),
            lefthook.index("format-staged-node"),
            lefthook.index("lint-project-node"),
            lefthook.index("type-check-project"),
        ]
        self.assertEqual(sorted(order), order)
        self.assertNotIn("vitest", lefthook)
        self.assertNotIn("pnpm exec tsc -p tsconfig.build.json", lefthook)
        self.assertNotIn("stage_fixed", lefthook)
        self.assertNotIn("{staged_files}", lefthook)
        formatter = (target / ".lefthook" / "format-staged-node.mjs").read_text(
            encoding="utf-8"
        )
        self.assertIn('"--name-only", "--diff-filter=ACMR", "-z"', formatter)
        self.assertIn('spawnSync("pnpm", ["exec", "oxfmt"', formatter)
        self.assertIn('spawnSync("git", ["add", "--", ...files]', formatter)
        installer = (target / ".lefthook" / "install-node.mjs").read_text(
            encoding="utf-8"
        )
        self.assertIn('spawnSync("lefthook", ["install", "--force"]', installer)
        self.assertIn("--no-stage-fixed", installer)
        self.assertTrue((target / ".github" / "renovate.json").is_file())
        self.assertTrue((target / "pnpm-lock.yaml").is_file())

    def preserved_hashes(self, target: Path) -> dict[str, str]:
        paths = (
            "README.md",
            "src/index.ts",
            "test/index.test.ts",
            "tsconfig.json",
            "vitest.config.ts",
        )
        return {
            path: hashlib.sha256((target / path).read_bytes()).hexdigest()
            for path in paths
        }


if __name__ == "__main__":
    unittest.main()
