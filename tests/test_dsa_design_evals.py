from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

from scripts.run_behavior_evals import evaluate_answer


ROOT = Path(__file__).resolve().parents[1]


class DsaDesignEvalsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        contract = json.loads((ROOT / "evals/dsa-design.behavior.json").read_text())
        cls.cases = {case["id"]: case for case in contract["cases"]}

    def failures(self, case_id: str, answer: str) -> list[str]:
        assertions = self.cases[case_id]["expected"]["assertions"]
        flags = re.IGNORECASE | re.MULTILINE
        return evaluate_answer(
            answer,
            [re.compile(pattern, flags) for pattern in assertions["required_regex"]],
            [re.compile(pattern, flags) for pattern in assertions["forbidden_regex"]],
        )

    def test_fixed_answers_pass(self) -> None:
        for case_id in self.cases:
            with self.subTest(case=case_id):
                answer = (ROOT / f"evals/fixtures/dsa-design/{case_id}.txt").read_text()
                self.assertEqual([], self.failures(case_id, answer))

    def test_old_bucket_only_exact_design_is_rejected(self) -> None:
        answer = (
            "Final design adopts minute ring buckets, each keeping the highest-scoring "
            "records in a min-heap of capacity 100; on query, merge active buckets and "
            "take Top-100. Per-event updates are O(log 100) and memory stays bounded. "
            "Verify tied scores, window boundaries, late events, and peak throughput."
        )
        self.assertTrue(self.failures("delegated-choice-no-pause", answer))

    def test_frequency_sketch_is_not_a_score_ranking_answer(self) -> None:
        answer = (
            "Recommend Space-Saving for exact score ranking with frequency counts. "
            "Use a min-heap and O(N log K) processing."
        )
        self.assertTrue(self.failures("score-versus-frequency", answer))

    def test_wrong_expiration_answer_is_rejected(self) -> None:
        answer = (
            "The correct answer is A. B expired and was discarded at the partial "
            "boundary. Keep raw records and compare with a full sort baseline."
        )
        self.assertTrue(self.failures("sliding-window-boundary-counterexample", answer))

    def test_live_equivalent_phrasings_are_accepted(self) -> None:
        variants = {
            "dependency-cycle-before-execution": (
                ("before executing any task", "先完整校验，再调度"),
                ("preflight succeeds", "全图检查通过"),
            ),
            "sliding-window-boundary-counterexample": (
                ("discarded B", "B 已不可恢复"),
            ),
        }
        for case_id, replacements in variants.items():
            with self.subTest(case=case_id):
                answer = (ROOT / f"evals/fixtures/dsa-design/{case_id}.txt").read_text()
                for old, new in replacements:
                    self.assertIn(old, answer)
                    answer = answer.replace(old, new)
                self.assertEqual([], self.failures(case_id, answer))

        case_id = "dependency-cycle-before-execution"
        answer = (ROOT / f"evals/fixtures/dsa-design/{case_id}.txt").read_text()
        answer = answer.replace(
            "before executing any task",
            "先完整校验，再生成执行顺序；校验通过前不执行任何任务",
        ).replace("preflight succeeds", "全图检查通过")
        self.assertEqual([], self.failures(case_id, answer))

    def test_documented_bucket_counterexample(self) -> None:
        # Independently compute the reference answer and the lossy bucket answer.
        records = [("A", 0, 10), ("B", 30, 9)]
        now, window = 3601, 3600
        active = [record for record in records if now - window < record[1] <= now]
        exact = max(active, key=lambda record: record[2])
        bucket_top = max(records, key=lambda record: record[2])
        retained = [bucket_top] if now - window < bucket_top[1] <= now else []
        self.assertEqual("B", exact[0])
        self.assertEqual([], retained)

    def test_relevant_required_fact_cannot_be_omitted(self) -> None:
        omissions = {
            "cache-byte-budget-and-invalidation": (
                "a generation token. Invalidation advances the generation; an older "
                "load cannot publish into a newer generation.",
                "an unconditional write when loading completes.",
            ),
            "dependency-cycle-before-execution": ("B -> A", "A -> B"),
            "external-memory-exact-dedup": (
                "Size chunks by bytes, leaving RAM for the 1 MiB maximum record, "
                "sorting overhead and bounded merge buffers. Bound merge fan-in "
                "and file descriptors;",
                "Use default chunk sizes and merge everything in one pass;",
            ),
            "concurrent-bounded-queue": ("atomic", "separate"),
            "benchmark-evidence-boundary": ("have not run", "are complete"),
        }
        for case_id, (old, new) in omissions.items():
            with self.subTest(case=case_id):
                answer = (ROOT / f"evals/fixtures/dsa-design/{case_id}.txt").read_text()
                self.assertIn(old, answer)
                self.assertTrue(self.failures(case_id, answer.replace(old, new)))


if __name__ == "__main__":
    unittest.main()
