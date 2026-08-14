#!/usr/bin/env python3

from __future__ import annotations

import binascii
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import textwrap
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = (
    ROOT
    / "skills"
    / "creative"
    / "juanjuan-illustrations"
    / "scripts"
    / "validate_artifact.py"
)


class ValidateJuanjuanArtifactTest(unittest.TestCase):
    def test_valid_png_and_prompt_record_pass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="juanjuan-artifact-test-") as directory:
            directory_path = Path(directory)
            image_path = directory_path / "01-sample.png"
            record_path = directory_path / "01-sample.prompt.md"
            self.write_png(image_path, width=160, height=90)
            self.write_record(record_path, image_path)

            completed = self.run_validator(image_path)

        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("PASS", completed.stdout)
        self.assertIn("160x90", completed.stdout)

    def test_missing_source_fact_field_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="juanjuan-artifact-test-") as directory:
            directory_path = Path(directory)
            image_path = directory_path / "01-sample.png"
            record_path = directory_path / "01-sample.prompt.md"
            self.write_png(image_path, width=160, height=90)
            self.write_record(record_path, image_path)
            record_path.write_text(
                record_path.read_text(encoding="utf-8").replace(
                    "allowed_labels: none\n",
                    "",
                ),
                encoding="utf-8",
            )

            completed = self.run_validator(image_path)

        self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("allowed_labels", completed.stdout)

    def test_failed_qa_record_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="juanjuan-artifact-test-") as directory:
            directory_path = Path(directory)
            image_path = directory_path / "01-sample.png"
            record_path = directory_path / "01-sample.prompt.md"
            self.write_png(image_path, width=160, height=90)
            self.write_record(record_path, image_path)
            record_path.write_text(
                record_path.read_text(encoding="utf-8").replace(
                    "- result: pass",
                    "- result: fail",
                ),
                encoding="utf-8",
            )

            completed = self.run_validator(image_path)

        self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("QA result must be pass", completed.stdout)

    def test_missing_required_record_section_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="juanjuan-artifact-test-") as directory:
            directory_path = Path(directory)
            image_path = directory_path / "01-sample.png"
            record_path = directory_path / "01-sample.prompt.md"
            self.write_png(image_path, width=160, height=90)
            self.write_record(record_path, image_path)
            record_path.write_text(
                record_path.read_text(encoding="utf-8").replace(
                    "## 最终提示词\n",
                    "",
                ),
                encoding="utf-8",
            )

            completed = self.run_validator(image_path)

        self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("最终提示词", completed.stdout)

    def test_mismatched_final_output_path_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="juanjuan-artifact-test-") as directory:
            directory_path = Path(directory)
            image_path = directory_path / "01-sample.png"
            record_path = directory_path / "01-sample.prompt.md"
            self.write_png(image_path, width=160, height=90)
            self.write_record(record_path, image_path)
            record_path.write_text(
                record_path.read_text(encoding="utf-8").replace(
                    str(image_path.resolve()),
                    str((directory_path / "other.png").resolve()),
                ),
                encoding="utf-8",
            )

            completed = self.run_validator(image_path)

        self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("final output path", completed.stdout)

    def test_source_fact_field_outside_source_card_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="juanjuan-artifact-test-") as directory:
            directory_path = Path(directory)
            image_path = directory_path / "01-sample.png"
            record_path = directory_path / "01-sample.prompt.md"
            self.write_png(image_path, width=160, height=90)
            self.write_record(record_path, image_path)
            record = record_path.read_text(encoding="utf-8")
            record = record.replace("allowed_labels: none\n", "")
            record = record.replace(
                "Test prompt\n",
                "Test prompt\nallowed_labels: none\n",
            )
            record_path.write_text(record, encoding="utf-8")

            completed = self.run_validator(image_path)

        self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("allowed_labels", completed.stdout)

    def test_aspect_ratio_outside_tolerance_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="juanjuan-artifact-test-") as directory:
            directory_path = Path(directory)
            image_path = directory_path / "01-sample.png"
            record_path = directory_path / "01-sample.prompt.md"
            self.write_png(image_path, width=120, height=90)
            self.write_record(record_path, image_path)

            completed = self.run_validator(image_path)

        self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("aspect-ratio error", completed.stdout)

    def run_validator(self, image_path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(image_path)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def write_record(self, record_path: Path, image_path: Path) -> None:
        record_path.write_text(
            textwrap.dedent(
                f"""
                # {image_path.name}

                ## 来源锚点

                测试原文

                ## 来源事实卡

                core_claim: 测试判断
                exact_terms: none
                required_relationships: none
                required_counts: none
                unsupported_inferences: none
                script: none
                allowed_labels: none

                ## 最终提示词

                Test prompt

                ## 参考与工具

                - reference: skills/creative/juanjuan-illustrations/assets/juanjuan-character-reference-v3.png
                - tool: test

                ## QA

                - result: pass
                - notes: deterministic fixture

                ## 迭代记录

                none

                ## 最终输出

                {image_path.resolve()}
                """
            ).lstrip(),
            encoding="utf-8",
        )

    def write_png(self, path: Path, width: int, height: int) -> None:
        def chunk(chunk_type: bytes, data: bytes) -> bytes:
            checksum = binascii.crc32(chunk_type + data) & 0xFFFFFFFF
            return (
                struct.pack(">I", len(data))
                + chunk_type
                + data
                + struct.pack(">I", checksum)
            )

        header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
        scanlines = b"".join(b"\x00" + b"\x00\x00\x00" * width for _ in range(height))
        path.write_bytes(
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(scanlines))
            + chunk(b"IEND", b"")
        )


if __name__ == "__main__":
    unittest.main()
