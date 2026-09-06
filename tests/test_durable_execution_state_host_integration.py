from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/development/workflows/durable-execution-state/scripts"


def digest(request: dict) -> str:
    return hashlib.sha256(json.dumps(
        request, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


class DurableExecutionStateHostIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="statectl-host-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.approval_path = self.root / "approval.json"
        self.request = {
            "idempotency_key": "演练:一次", "tool": "local-simulation",
            "args": {"对象": "测试"}, "authorization_ref": "授权://测试/一",
            "preconditions": [],
        }
        self.payload = {"request": self.request, "request_sha256": digest(self.request)}
        self.approval = {
            "authorized": True, "authorization_ref": self.request["authorization_ref"],
            "request_sha256": digest(self.request), "verifier_ref": "host-policy://test-only",
            "expires_at": "2099-09-01T00:00:00Z",
        }

    def call_verifier(self, payload: dict, approval: dict) -> subprocess.CompletedProcess[str]:
        self.approval_path.write_text(json.dumps(approval), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "approval_file_verifier.py"),
             "--approval-file", str(self.approval_path)],
            input=json.dumps(payload), text=True, capture_output=True, timeout=10,
        )

    def test_example_accepts_bound_unicode_request(self) -> None:
        result = self.call_verifier(self.payload, self.approval)
        self.assertEqual(0, result.returncode, result.stderr)
        proof = json.loads(result.stdout)
        self.assertTrue(proof["authorized"])
        self.assertEqual(self.request["authorization_ref"], proof["authorization_ref"])
        self.assertEqual(digest(self.request), proof["request_sha256"])

    def test_example_denies_changed_requests_and_invalid_approvals(self) -> None:
        changed_request = {**self.request, "args": {"对象": "另一个对象"}}
        cases = [
            ({**self.payload, "request_sha256": "0" * 64}, self.approval),
            ({"request": changed_request, "request_sha256": digest(changed_request)}, self.approval),
            (self.payload, {**self.approval, "authorization_ref": "授权://另一个批准"}),
            (self.payload, {**self.approval, "expires_at": "2000-01-01T00:00:00Z"}),
            (self.payload, {**self.approval, "expires_at": "2099-9-1T00:00:00Z"}),
            (self.payload, {**self.approval, "authorized": False}),
            (self.payload, {key: value for key, value in self.approval.items() if key != "request_sha256"}),
        ]
        for index, (payload, approval) in enumerate(cases):
            with self.subTest(case=index):
                result = self.call_verifier(payload, approval)
                self.assertEqual(1, result.returncode)
                self.assertEqual("", result.stdout)
                self.assertIn("DENIED", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_host_pinned_wrapper_connects_to_public_cli(self) -> None:
        self.approval_path.write_text(json.dumps(self.approval), encoding="utf-8")
        wrapper = self.root / "test-only-verifier"
        verifier = SCRIPTS / "approval_file_verifier.py"
        wrapper.write_text(
            f"#!{sys.executable}\nimport runpy, sys\n"
            f"sys.argv = [{str(verifier)!r}, '--approval-file', {str(self.approval_path)!r}]\n"
            f"runpy.run_path({str(verifier)!r}, run_name='__main__')\n",
            encoding="utf-8",
        )
        wrapper.chmod(0o700)
        criteria = self.root / "criteria.json"
        criteria.write_text('[{"id":"done","description":"test only"}]', encoding="utf-8")
        action = self.root / "action.json"
        action.write_text(json.dumps(self.request), encoding="utf-8")
        store = self.root / "store"
        environment = os.environ.copy()
        environment.pop("STATECTL_FAULT_POINT", None)
        commands = [
            ["init", "--store", str(store), "--task-id", "test-only", "--objective", "test only",
             "--criteria-file", str(criteria)],
            ["begin-action", "--store", str(store), "--expected-version", "0", "--action-file",
             str(action), "--authorization-verifier", str(wrapper)],
            ["verify", "--store", str(store)],
        ]
        for command in commands:
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "statectl.py"), *command],
                env=environment, text=True, capture_output=True, timeout=10,
            )
            self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(json.loads(result.stdout)["verified"])
        # No external executor is invoked; the action remains a recorded intent.
        state = json.loads((store / "state.snapshot.json").read_text())
        self.assertEqual(1, len(state["pending_actions"]))

    def test_disposable_rehearsal_recovers_without_real_external_actions(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "rehearse_recovery.py"), "--steps", "3"],
            text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(7, report["final_state_version"])
        self.assertEqual(8, report["event_count"])
        self.assertEqual(0, report["real_external_actions"])
        self.assertFalse(report["host_trust_verified"])
        self.assertTrue(report["verified"])
        self.assertEqual("complete", report["task_status"])
        self.assertEqual(6, len(report["checks"]))
        self.assertLessEqual(report["peak_patch_state_bytes"], 65536)


if __name__ == "__main__":
    unittest.main()
