from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "development" / "workflows" / "bootstrap-project"
ASSETS = SKILL / "assets"
STACKS = ("zig", "rust", "node", "python", "go")
PUBLIC_TASKS = {
    "format",
    "format-check",
    "lint",
    "check",
    "test",
    "build",
    "ci",
}
HOOK_JOBS = {
    "zig": (
        "partial-stage-guard",
        "format-staged-zig",
        "lint-staged-zig",
        "quick-project-check",
    ),
    "rust": (
        "partial-stage-guard",
        "format-staged-rust",
        "lint-project-rust",
        "quick-project-check",
    ),
    "node": (
        "partial-stage-guard",
        "format-staged-node",
        "lint-project-node",
        "type-check-project",
    ),
    "python": (
        "partial-stage-guard",
        "format-staged-python",
        "lint-project-python",
        "type-check-project",
    ),
    "go": (
        "partial-stage-guard",
        "format-staged-go",
        "check-module-metadata",
        "vet-project",
    ),
}
HOOK_HELPERS = {
    "zig": ("install-hooks.sh.tmpl", "format-staged-zig.sh.tmpl"),
    "rust": ("install-hooks.sh.tmpl", "format-staged-rust.sh.tmpl"),
    "node": ("install-node.mjs.tmpl", "format-staged-node.mjs.tmpl"),
    "python": ("install_python.py.tmpl", "format_staged_python.py.tmpl"),
    "go": ("install_go.go.tmpl", "format_staged_go.go.tmpl"),
}


class BootstrapProjectIntegrationTests(unittest.TestCase):
    def test_skill_entrypoint_uses_progressive_disclosure(self) -> None:
        source = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(source.splitlines()), 100)
        self.assertIn("read exactly one stack reference completely", source)
        for reference in (
            "stack-evidence.md",
            "zig.md",
            "zig-existing.md",
            "rust.md",
            "node.md",
            "python.md",
            "go.md",
            "reporting.md",
        ):
            self.assertIn(f"(references/{reference})", source)
        for disclosed_detail in (
            "MISE_TRUSTED_CONFIG_PATHS",
            "cargo init",
            "pnpm-lock.yaml",
            "uv.lock",
            "GOTOOLCHAIN",
            "addRunArtifact",
        ):
            self.assertNotIn(disclosed_detail, source)

    def test_every_stack_exposes_the_same_public_task_contract(self) -> None:
        for stack in STACKS:
            with self.subTest(stack=stack):
                source = self._read(stack, "mise.toml.tmpl")
                names = set(re.findall(r"(?m)^\[tasks\.([^]]+)]$", source))
                self.assertTrue(PUBLIC_TASKS <= names)
                for task in PUBLIC_TASKS:
                    body = self._task_body(source, task)
                    self.assertRegex(body, r"(?m)^run\s*=\s*\S")
                ci = self._task_body(source, "ci")
                self.assertNotIn('{ task = "format" }', ci)
                for task in ("format-check", "lint", "check", "test", "build"):
                    self.assertIn(f'{{ task = "{task}" }}', ci)

    def test_every_pre_commit_is_a_safe_short_pipeline(self) -> None:
        for stack in STACKS:
            with self.subTest(stack=stack):
                source = self._read(stack, "lefthook.yml.tmpl")
                self.assertIn("piped: true", source)
                self.assertNotIn("stage_fixed", source)
                self.assertNotIn("mise run test", source)
                self.assertNotIn("mise run build", source)
                positions = [source.index(name) for name in HOOK_JOBS[stack]]
                self.assertEqual(sorted(positions), positions)

                helper_root = ASSETS / stack / "common" / ".lefthook"
                installer_name, formatter_name = HOOK_HELPERS[stack]
                installer = (helper_root / installer_name).read_text(encoding="utf-8")
                formatter = (helper_root / formatter_name).read_text(encoding="utf-8")
                self.assertIn("--no-stage-fixed", installer)
                self.assertIn("MISE_TRUSTED_CONFIG_PATHS", installer)
                self.assertIn("--cached", formatter)
                self.assertIn("-z", formatter)
                self.assertIn("add", formatter)
                if stack == "zig":
                    self.assertIn('zig fmt "./$file"', formatter)

    def test_every_workflow_is_ubuntu_only_sha_pinned_and_has_one_entry(self) -> None:
        action = re.compile(
            r"(?m)^\s*(?:-\s+)?uses:\s*[^@\s]+@([0-9a-f]{40})(?:\s|$)"
        )
        for stack in STACKS:
            with self.subTest(stack=stack):
                workflow = self._read(stack, ".github/workflows/validate.yml.tmpl")
                self.assertEqual(1, workflow.count("runs-on: ubuntu-latest"))
                self.assertNotIn("matrix:", workflow)
                self.assertEqual(1, workflow.count("run: mise run ci"))
                self.assertGreaterEqual(len(action.findall(workflow)), 2)
                uses_lines = [
                    line.strip() for line in workflow.splitlines() if "uses:" in line
                ]
                self.assertTrue(uses_lines)
                self.assertTrue(all(action.search(line) for line in uses_lines))

    def test_every_renovate_config_has_the_confirmed_safe_defaults(self) -> None:
        forbidden = {"automerge", "autoApprove", "schedule"}
        for stack in STACKS:
            with self.subTest(stack=stack):
                config = json.loads(self._read(stack, ".github/renovate.json.tmpl"))
                self.assertEqual(["config:recommended"], config["extends"])
                self.assertEqual("enabled", config["semanticCommits"])
                self.assertEqual(["dependencies"], config["labels"])
                self.assertEqual({"enabled": False}, config["lockFileMaintenance"])
                self.assertTrue(forbidden.isdisjoint(config))

    def test_behavior_matrix_covers_new_library_cli_and_existing_per_stack(self) -> None:
        contract = json.loads(
            (ROOT / "evals" / "bootstrap-project.behavior.json").read_text(
                encoding="utf-8"
            )
        )
        ids = {case["id"] for case in contract["cases"]}
        for stack in STACKS:
            with self.subTest(stack=stack):
                self.assertIn(f"new-{stack}-library", ids)
                self.assertIn(f"new-{stack}-cli", ids)
                self.assertIn(f"existing-{stack}-baseline", ids)

    def test_acceptance_record_states_platform_and_evidence_boundaries(self) -> None:
        source = (ROOT / "docs" / "bootstrap-project-acceptance.md").read_text(
            encoding="utf-8"
        )
        for required in (
            "macOS",
            "Linux",
            "Windows",
            "不支持",
            "真实 smoke",
            "live Codex",
            "补充证据",
            "副作用",
        ):
            self.assertIn(required, source)

    def _read(self, stack: str, relative: str) -> str:
        return (ASSETS / stack / "common" / relative).read_text(encoding="utf-8")

    def _task_body(self, source: str, task: str) -> str:
        match = re.search(
            rf"(?ms)^\[tasks\.{re.escape(task)}]\n(.*?)(?=^\[|\Z)",
            source,
        )
        self.assertIsNotNone(match, task)
        return match.group(1)


if __name__ == "__main__":
    unittest.main()
