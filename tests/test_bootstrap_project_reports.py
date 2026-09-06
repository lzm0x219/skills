from __future__ import annotations

import argparse
from contextlib import redirect_stderr
import importlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/development/workflows/bootstrap-project/scripts"
sys.path.insert(0, str(SCRIPTS))
ADAPTERS = (
    "bootstrap_zig", "baseline_existing_zig", "bootstrap_rust",
    "bootstrap_node", "bootstrap_python", "bootstrap_go",
)


class ReportPreservationTest(unittest.TestCase):
    def test_all_adapters_reject_occupied_report_before_initialization(self) -> None:
        for name in ADAPTERS:
            for kind in ("file", "directory", "symlink", "dangling-symlink"):
                with self.subTest(adapter=name, kind=kind), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    owned = root / "owned.txt"
                    owned.write_text("keep", encoding="utf-8")
                    report = root / "report.json"
                    if kind == "file":
                        report.write_text("previous evidence", encoding="utf-8")
                    elif kind == "directory":
                        report.mkdir()
                    else:
                        report.symlink_to(owned if kind == "symlink" else root / "missing")
                    target = root / "project"
                    options = argparse.Namespace(target=target, report=report)
                    module = importlib.import_module(name)
                    stderr = io.StringIO()
                    with patch.object(module, "parse_args", return_value=options), redirect_stderr(stderr):
                        self.assertEqual(2, module.main())
                    self.assertIn("--report", stderr.getvalue())
                    self.assertFalse(target.exists())
                    self.assertEqual("keep", owned.read_text(encoding="utf-8"))
                    if kind == "file":
                        self.assertEqual("previous evidence", report.read_text(encoding="utf-8"))
                    if "symlink" in kind:
                        self.assertTrue(report.is_symlink())

    def test_report_writer_refuses_late_collision(self) -> None:
        module = importlib.import_module("bootstrap_zig")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            module.write_report(path, {"status": "partial"})
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                module.write_report(path, {"status": "completed"})
            self.assertEqual(original, path.read_bytes())
