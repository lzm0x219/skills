#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Callable
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ValidateSkillsTest(unittest.TestCase):
    def test_current_repository_is_valid(self) -> None:
        completed = self.run_validator(ROOT)

        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)

    def test_source_assertions_cover_bundled_text_resources(self) -> None:
        for filename in ("extra.rs", "extra.cjs", "extra.bash", "executable"):
            with self.subTest(filename=filename), self.copied_repo() as repo:
                resource_path = (
                    repo / "skills" / "framework" / "napi-rs" / filename
                )
                resource_path.write_text("仅支持 repolex 仓库。\n", encoding="utf-8")

                completed = self.run_validator(repo)

                self.assertNotEqual(0, completed.returncode, f"{filename} was not scanned")
                self.assertIn(
                    "Skill source matches forbidden pattern",
                    completed.stdout + completed.stderr,
                )

    def test_required_case_invocation_cannot_change(self) -> None:
        def mutate(contract: dict[str, object]) -> None:
            target = next(
                entry
                for entry in contract["cases"]
                if entry["id"] == "unapproved-release"
            )
            target["invocation"] = "implicit"

        self.assert_contract_rejected(
            mutate,
            expected_message="unapproved-release invocation must be explicit",
        )

    def test_frontmatter_must_be_a_mapping(self) -> None:
        with self.copied_repo() as repo:
            skill_path = repo / "skills" / "framework" / "napi-rs" / "SKILL.md"
            source = skill_path.read_text(encoding="utf-8")
            skill_path.write_text(
                re.sub(
                    r"\A---\n.*?\n---",
                    "---\nfalse\n---",
                    source,
                    count=1,
                    flags=re.DOTALL,
                ),
                encoding="utf-8",
            )

            completed = self.run_validator(repo)

            self.assertNotEqual(0, completed.returncode)
            self.assertIn(
                "frontmatter must be a YAML mapping",
                completed.stdout + completed.stderr,
            )

    def test_required_behavior_cases_cannot_be_removed(self) -> None:
        def mutate(contract: dict[str, object]) -> None:
            contract["cases"] = [
                entry
                for entry in contract["cases"]
                if entry["id"] != "top-k-material-decision"
            ]

        self.assert_contract_rejected(
            mutate,
            skill_name="dsa-design",
            expected_message="missing required cases: top-k-material-decision",
        )

    def test_unknown_nested_contract_fields_are_rejected(self) -> None:
        mutations: dict[str, Callable[[dict[str, object]], None]] = {
            "execution": lambda contract: contract["execution"].update(extra=True),
            "case": lambda contract: contract["cases"][0].update(extra=True),
            "expected": lambda contract: contract["cases"][0]["expected"].update(
                extra=True
            ),
            "assertions": lambda contract: contract["cases"][0]["expected"][
                "assertions"
            ].update(extra=[]),
        }

        for level, mutate in mutations.items():
            with self.subTest(level=level):
                self.assert_contract_rejected(
                    mutate,
                    expected_message="unexpected keys: extra",
                    failure_message=f"{level} accepted an unknown field",
                )

    def test_unknown_contract_fields_are_rejected(self) -> None:
        self.assert_contract_rejected(
            lambda contract: contract.update(unverified_behavior=True),
            expected_message="unexpected keys: unverified_behavior",
        )

    def test_execution_description_must_be_a_non_empty_string(self) -> None:
        self.assert_contract_rejected(
            lambda contract: contract["execution"].update(description=""),
            expected_message="execution.description must be a non-empty string",
        )

    def test_case_category_must_be_a_non_empty_string(self) -> None:
        self.assert_contract_rejected(
            lambda contract: contract["cases"][0].update(category=""),
            expected_message="category must be a non-empty string",
        )

    def test_source_assertions_are_required(self) -> None:
        self.assert_contract_rejected(
            lambda contract: contract.pop("source_assertions"),
            expected_message="source_assertions must be an object",
        )

    def test_source_assertions_reject_a_project_specific_napi_skill(self) -> None:
        with self.copied_repo() as repo:
            skill_path = repo / "skills" / "framework" / "napi-rs" / "SKILL.md"
            source = skill_path.read_text(encoding="utf-8")
            skill_path.write_text(
                source.replace("不要假定某个仓库", "仅支持 repolex 仓库", 1),
                encoding="utf-8",
            )

            completed = self.run_validator(repo)
            output = completed.stdout + completed.stderr

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("Skill source is missing required pattern", output)
            self.assertIn("Skill source matches forbidden pattern", output)

    def test_source_assertions_lock_napi_safety_rules(self) -> None:
        mutations = {
            "官方文档路由": (
                "涉及 CLI、Cargo feature、目标平台、WASI、发布或迁移时，始终以当前官方页面为准；",
                "",
            ),
            "发布授权边界": ("没有用户的明确授权，不运行它们。", ""),
        }

        for rule, (source, replacement) in mutations.items():
            with self.subTest(rule=rule), self.copied_repo() as repo:
                skill_path = (
                    repo / "skills" / "framework" / "napi-rs" / "SKILL.md"
                )
                skill_path.write_text(
                    skill_path.read_text(encoding="utf-8").replace(
                        source,
                        replacement,
                        1,
                    ),
                    encoding="utf-8",
                )

                completed = self.run_validator(repo)

                self.assertNotEqual(
                    0,
                    completed.returncode,
                    f"removing {rule} did not fail validation",
                )
                self.assertIn(
                    "Skill source is missing required pattern",
                    completed.stdout + completed.stderr,
                )

    def assert_contract_rejected(
        self,
        mutate: Callable[[dict[str, object]], object],
        *,
        expected_message: str,
        skill_name: str = "napi-rs",
        failure_message: str | None = None,
    ) -> None:
        with self.copied_repo() as repo:
            contract_path = repo / "evals" / f"{skill_name}.behavior.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            mutate(contract)
            contract_path.write_text(
                json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            completed = self.run_validator(repo)

            self.assertNotEqual(0, completed.returncode, failure_message)
            self.assertIn(
                expected_message,
                completed.stdout + completed.stderr,
            )

    @staticmethod
    def run_validator(repo: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(repo / "scripts" / "validate_skills.py")],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )

    @staticmethod
    def copied_repo() -> tempfile.TemporaryDirectory[str]:
        class CopiedRepository(tempfile.TemporaryDirectory[str]):
            def __enter__(self) -> Path:
                directory = Path(super().__enter__())
                copy = directory / "repo"
                shutil.copytree(
                    ROOT,
                    copy,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
                )
                return copy

        return CopiedRepository(prefix="validate-skills-test-")


if __name__ == "__main__":
    unittest.main()
