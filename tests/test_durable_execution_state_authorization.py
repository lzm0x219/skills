#!/usr/bin/env python3

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
STATECTL = (
    ROOT
    / "skills"
    / "development"
    / "workflows"
    / "durable-execution-state"
    / "scripts"
    / "statectl.py"
)
sys.path.insert(0, str(STATECTL.parent))
from statectl_runtime.authorization import (  # noqa: E402
    reference_authorization,
    validate_recorded_authorization,
)
from statectl_runtime.errors import StateError  # noqa: E402


class DurableExecutionStateAuthorizationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="durable-execution-state-authorization-test-"
        )
        self.root = Path(self.temporary.name)
        self.store = self.root / "store"
        self.criteria = self.write_json(
            "criteria.json",
            [{"id": "done", "description": "The task is done"}],
        )
        self.run_statectl(
            "init",
            "--store",
            str(self.store),
            "--task-id",
            "authorization-test",
            "--objective",
            "Exercise authorization behavior",
            "--criteria-file",
            str(self.criteria),
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_existing_action_is_reused_without_revalidating_authorization(self) -> None:
        action = self.write_json(
            "action.json",
            {
                "idempotency_key": "deploy:release-1",
                "tool": "deploy",
                "args": {"release": "1"},
                "authorization_ref": "approval://release-1",
                "preconditions": [],
            },
        )
        verifier = self.write_verifier(
            "authorization-verifier.py",
            """
payload = json.load(sys.stdin)
print(json.dumps({
    "authorized": True,
    "authorization_ref": payload["request"]["authorization_ref"],
    "request_sha256": payload["request_sha256"],
    "verifier_ref": "host-policy://release/test",
    "verified_at": "2026-09-01T00:00:00Z"
}))
""",
        )
        begun = self.run_statectl(
            "begin-action",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--action-file",
            str(action),
            "--authorization-verifier",
            str(verifier),
        )
        verifier.unlink()

        repeated = self.run_statectl(
            "begin-action",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--action-file",
            str(action),
        )

        self.assertTrue(repeated["reused"])
        self.assertEqual(begun["action_id"], repeated["action_id"])
        self.assertEqual(1, repeated["state_version"])

        new_action = self.write_json(
            "new-action.json",
            {
                **json.loads(action.read_text(encoding="utf-8")),
                "idempotency_key": "deploy:release-2",
            },
        )
        rejected = self.run_statectl_raw(
            "begin-action",
            "--store",
            str(self.store),
            "--expected-version",
            "1",
            "--action-file",
            str(new_action),
        )
        self.assertEqual(2, rejected.returncode)
        self.assertIn("authorization verifier is required", rejected.stderr)

    def test_verifier_rejects_non_string_authorization_reference(self) -> None:
        action = self.write_json(
            "typed-action.json",
            {
                "idempotency_key": "deploy:typed",
                "tool": "deploy",
                "args": {},
                "authorization_ref": "7",
                "preconditions": [],
            },
        )
        verifier = self.write_verifier(
            "numeric-reference-verifier.py",
            """
payload = json.load(sys.stdin)
print(json.dumps({
    "authorized": True,
    "authorization_ref": 7,
    "request_sha256": payload["request_sha256"],
    "verifier_ref": "host-policy://release/test",
    "verified_at": "2026-09-01T00:00:00Z"
}))
""",
        )

        rejected = self.run_statectl_raw(
            "begin-action",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--action-file",
            str(action),
            "--authorization-verifier",
            str(verifier),
        )

        self.assertEqual(2, rejected.returncode)
        self.assertIn("authorization_ref must be a string", rejected.stderr)
        state = self.run_statectl("show", "--store", str(self.store))
        self.assertEqual({}, state["pending_actions"])

    def test_verifier_rejects_non_rfc3339_timestamp(self) -> None:
        action = self.write_json(
            "timestamp-action.json",
            {
                "idempotency_key": "deploy:timestamp",
                "tool": "deploy",
                "args": {},
                "authorization_ref": "approval://timestamp",
                "preconditions": [],
            },
        )
        verifier = self.write_verifier(
            "space-separated-timestamp-verifier.py",
            """
payload = json.load(sys.stdin)
print(json.dumps({
    "authorized": True,
    "authorization_ref": payload["request"]["authorization_ref"],
    "request_sha256": payload["request_sha256"],
    "verifier_ref": "host-policy://release/test",
    "verified_at": "2026-09-01 00:00:00Z"
}))
""",
        )

        rejected = self.run_statectl_raw(
            "begin-action",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--action-file",
            str(action),
            "--authorization-verifier",
            str(verifier),
        )

        self.assertEqual(2, rejected.returncode)
        self.assertIn("must be an RFC 3339 timestamp", rejected.stderr)

    def test_reference_authorization_warns_that_it_cannot_authorize_execution(
        self,
    ) -> None:
        action = self.write_json(
            "reference-action.json",
            {
                "idempotency_key": "deploy:reference-only",
                "tool": "deploy",
                "args": {},
                "authorization_ref": "rehearsal://release-1",
                "preconditions": [],
            },
        )

        completed = self.run_statectl_raw(
            "begin-action",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--action-file",
            str(action),
            "--allow-reference-authorization",
        )

        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn(
            "reference-only authorization does not authorize external execution",
            completed.stderr,
        )

    def test_unicode_authorization_reference_survives_begin_and_replay(self) -> None:
        action = self.write_json(
            "unicode-action.json",
            {
                "idempotency_key": "演练:发布一",
                "tool": "rehearsal",
                "args": {"名称": "样例"},
                "authorization_ref": "approval://用户/确认一",
                "preconditions": [],
            },
        )
        verifier = self.write_verifier(
            "unicode-verifier.py",
            """
payload = json.load(sys.stdin)
print(json.dumps({
    "authorized": True,
    "authorization_ref": payload["request"]["authorization_ref"],
    "request_sha256": payload["request_sha256"],
    "verifier_ref": "host-policy://test-only",
    "verified_at": "2026-09-01T00:00:00Z"
}))
""",
        )
        self.run_statectl(
            "begin-action", "--store", str(self.store), "--expected-version", "0",
            "--action-file", str(action), "--authorization-verifier", str(verifier),
        )
        self.assertTrue(self.run_statectl("verify", "--store", str(self.store))["verified"])

    def test_missing_verifier_field_with_optional_expiry_is_cleanly_rejected(self) -> None:
        action = self.write_json(
            "missing-field-action.json",
            {
                "idempotency_key": "rehearsal:missing-field",
                "tool": "rehearsal", "args": {},
                "authorization_ref": "approval://test", "preconditions": [],
            },
        )
        for missing in (
            "authorized", "authorization_ref", "request_sha256", "verifier_ref", "verified_at"
        ):
            with self.subTest(missing=missing):
                verifier = self.write_verifier(
                    "missing-field-verifier.py",
                    """
payload = json.load(sys.stdin)
response = {
    "authorized": True,
    "authorization_ref": payload["request"]["authorization_ref"],
    "request_sha256": payload["request_sha256"],
    "verifier_ref": "host-policy://test-only",
    "verified_at": "2026-09-01T00:00:00Z",
    "expires_at": "2099-09-01T00:00:00Z"
}
""" + f"del response[{missing!r}]\nprint(json.dumps(response))\n",
                )
                result = self.run_statectl_raw(
                    "begin-action", "--store", str(self.store), "--expected-version", "0",
                    "--action-file", str(action), "--authorization-verifier", str(verifier),
                )
                self.assertEqual(2, result.returncode, result.stderr)
                self.assertIn("response keys must include", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                state = self.run_statectl("show", "--store", str(self.store))
                self.assertEqual(0, state["state_version"])
                self.assertEqual({}, state["pending_actions"])

    def test_recorded_proof_requires_every_field_even_with_expiry(self) -> None:
        request = {
            "idempotency_key": "演练", "tool": "rehearsal", "args": {},
            "authorization_ref": "授权://测试", "preconditions": [],
        }
        proof = reference_authorization(request)
        proof["expires_at"] = "2099-09-01T00:00:00Z"
        self.assertEqual(proof, validate_recorded_authorization(proof, request))
        for missing in set(proof) - {"expires_at"}:
            with self.subTest(missing=missing):
                malformed = {key: value for key, value in proof.items() if key != missing}
                with self.assertRaisesRegex(StateError, "keys must include"):
                    validate_recorded_authorization(malformed, request)
        with self.assertRaisesRegex(StateError, "mode is invalid"):
            validate_recorded_authorization({**proof, "mode": []}, request)

    def test_verifier_invalid_utf8_is_cleanly_rejected(self) -> None:
        action = self.write_json("invalid-utf8-action.json", {
            "idempotency_key": "rehearsal:utf8", "tool": "rehearsal", "args": {},
            "authorization_ref": "approval://test", "preconditions": [],
        })
        verifier = self.write_verifier("invalid-utf8-verifier.py", "sys.stdout.buffer.write(bytes([255]))\n")
        result = self.run_statectl_raw(
            "begin-action", "--store", str(self.store), "--expected-version", "0",
            "--action-file", str(action), "--authorization-verifier", str(verifier),
        )
        self.assertEqual(2, result.returncode, result.stderr)
        self.assertIn("response must be UTF-8", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual({}, self.run_statectl("show", "--store", str(self.store))["pending_actions"])

    def test_cli_states_that_a_verifier_path_is_not_a_host_trust_boundary(self) -> None:
        completed = self.run_statectl_raw("begin-action", "--help")

        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertRegex(
            completed.stdout,
            r"path checks do not\s+establish host trust",
        )

    def write_json(self, name: str, value: object) -> Path:
        path = self.root / name
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def write_verifier(self, name: str, body: str) -> Path:
        path = self.root / name
        path.write_text(
            "#!/usr/bin/env python3\nimport json\nimport sys\n" + body.lstrip(),
            encoding="utf-8",
        )
        path.chmod(0o700)
        return path

    def run_statectl(self, *arguments: str) -> dict[str, object]:
        completed = self.run_statectl_raw(*arguments)
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertIsInstance(result, dict)
        return result

    @staticmethod
    def run_statectl_raw(*arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.pop("STATECTL_FAULT_POINT", None)
        return subprocess.run(
            [sys.executable, str(STATECTL), *arguments],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )


if __name__ == "__main__":
    unittest.main()
