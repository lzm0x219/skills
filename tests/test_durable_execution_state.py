#!/usr/bin/env python3

from __future__ import annotations

import json
import os
from pathlib import Path
import runpy
import shutil
import sqlite3
import stat
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


class DurableExecutionStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="durable-execution-state-test-"
        )
        self.root = Path(self.temporary.name)
        self.store = self.root / "store"
        self.criteria = self.write_json(
            "criteria.json",
            [{"id": "tests-pass", "description": "All tests pass"}],
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_init_show_and_verify(self) -> None:
        state = self.init_store()

        self.assertEqual(0, state["state_version"])
        self.assertEqual("active", state["task"]["status"])
        self.assertEqual("Ship safely", state["task"]["objective"])
        snapshot = json.loads(
            (self.store / "state.snapshot.json").read_text(encoding="utf-8")
        )
        self.assertEqual(state, snapshot)
        self.assertEqual(
            0o400,
            stat.S_IMODE((self.store / "state.snapshot.json").stat().st_mode),
        )
        self.assertEqual(
            0o600,
            stat.S_IMODE((self.store / "state.db").stat().st_mode),
        )

        verified = self.run_statectl("verify", "--store", str(self.store))

        self.assertTrue(verified["verified"])
        self.assertEqual("internal-store", verified["scope"])
        self.assertEqual(0, verified["pending_actions"])
        self.assertGreater(verified["state_size_bytes"], 0)
        self.assertLessEqual(verified["state_size_bytes"], 64 * 1024)

    def test_patch_is_local_and_rejects_stale_or_protected_writes(self) -> None:
        self.init_store()
        patch = self.write_json(
            "patch.json",
            [
                {
                    "op": "add",
                    "path": "/confirmed_facts/head",
                    "value": {
                        "value": "abc123",
                        "source_ref": "tool://git/rev-parse/1",
                        "observed_at": "2026-09-01T00:00:00Z",
                    },
                }
            ],
        )

        validated = self.run_statectl(
            "validate-patch",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--patch-file",
            str(patch),
        )
        self.assertTrue(validated["valid"])
        self.assertEqual(1, validated["candidate_state_version"])
        self.assertEqual(
            0,
            self.run_statectl("show", "--store", str(self.store))["state_version"],
        )

        state = self.run_statectl(
            "apply-patch",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--patch-file",
            str(patch),
        )

        self.assertEqual(1, state["state_version"])
        self.assertEqual("Ship safely", state["task"]["objective"])
        self.assertEqual("abc123", state["confirmed_facts"]["head"]["value"])

        stale = self.run_statectl_raw(
            "apply-patch",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--patch-file",
            str(patch),
        )
        self.assertEqual(2, stale.returncode)
        self.assertIn("stale state version", stale.stderr)

        protected = self.write_json(
            "protected.json",
            [{"op": "replace", "path": "/task/objective", "value": "Other"}],
        )
        rejected = self.run_statectl_raw(
            "apply-patch",
            "--store",
            str(self.store),
            "--expected-version",
            "1",
            "--patch-file",
            str(protected),
        )
        self.assertEqual(2, rejected.returncode)
        self.assertIn("patch path is protected", rejected.stderr)

        collection = self.write_json(
            "collection.json",
            [{"op": "replace", "path": "/confirmed_facts", "value": {}}],
        )
        rejected = self.run_statectl_raw(
            "apply-patch",
            "--store",
            str(self.store),
            "--expected-version",
            "1",
            "--patch-file",
            str(collection),
        )
        self.assertEqual(2, rejected.returncode)
        self.assertIn("cannot replace an entire state collection", rejected.stderr)

        remove_with_value = self.write_json(
            "remove-with-value.json",
            [
                {
                    "op": "remove",
                    "path": "/confirmed_facts/head",
                    "value": "must-not-be-present",
                }
            ],
        )
        rejected = self.run_statectl_raw(
            "apply-patch",
            "--store",
            str(self.store),
            "--expected-version",
            "1",
            "--patch-file",
            str(remove_with_value),
        )
        self.assertEqual(2, rejected.returncode)
        self.assertIn("invalid keys for remove", rejected.stderr)

    def test_action_requires_trusted_authorization_unless_explicitly_downgraded(
        self,
    ) -> None:
        self.init_store()
        action = self.write_json(
            "trusted-action.json",
            {
                "idempotency_key": "deploy:trusted",
                "tool": "deploy",
                "args": {"release": "1"},
                "authorization_ref": "approval://release-1",
                "preconditions": [],
            },
        )

        rejected = self.run_statectl_raw(
            "begin-action",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--action-file",
            str(action),
        )
        self.assertEqual(2, rejected.returncode)
        self.assertIn("trusted authorization verifier is required", rejected.stderr)

        verifier = self.root / "authorization-verifier.py"
        verifier.write_text(
            """#!/usr/bin/env python3
import json
import sys

payload = json.load(sys.stdin)
print(json.dumps({
    "authorized": True,
    "authorization_ref": payload["request"]["authorization_ref"],
    "request_sha256": payload["request_sha256"],
    "verifier_ref": "host-policy://release/test",
    "verified_at": "2026-09-01T00:00:00Z"
}))
""",
            encoding="utf-8",
        )
        verifier.chmod(0o700)

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
        state = self.run_statectl("show", "--store", str(self.store))
        authorization = state["pending_actions"][begun["action_id"]][
            "authorization_verification"
        ]
        self.assertEqual("trusted-verifier", authorization["mode"])
        self.assertEqual("host-policy://release/test", authorization["verifier_ref"])
        self.assertEqual(64, len(authorization["request_sha256"]))

    def test_authorization_verifier_response_is_bound_to_the_exact_request(
        self,
    ) -> None:
        self.init_store()
        action = self.write_json(
            "bound-action.json",
            {
                "idempotency_key": "deploy:bound",
                "tool": "deploy",
                "args": {"release": "1"},
                "authorization_ref": "approval://release-1",
                "preconditions": [],
            },
        )
        verifier = self.root / "mismatched-verifier.py"
        verifier.write_text(
            """#!/usr/bin/env python3
import json

print(json.dumps({
    "authorized": True,
    "authorization_ref": "approval://release-1",
    "request_sha256": "0" * 64,
    "verifier_ref": "host-policy://release/test",
    "verified_at": "2026-09-01T00:00:00Z"
}))
""",
            encoding="utf-8",
        )
        verifier.chmod(0o700)

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
        self.assertIn("request hash does not match", rejected.stderr)
        self.assertEqual(
            {},
            self.run_statectl("show", "--store", str(self.store))["pending_actions"],
        )

    def test_action_is_idempotent_and_confirmed_from_receipt(self) -> None:
        self.init_store()
        action = self.write_json(
            "action.json",
            {
                "idempotency_key": "deploy:release-1",
                "tool": "deploy",
                "args": {"release": "1"},
                "authorization_ref": "user-request://turn-1",
                "preconditions": [
                    {
                        "path": "/task/status",
                        "operator": "equals",
                        "value": "active",
                    }
                ],
            },
        )

        begun = self.run_statectl(
            "begin-action",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--action-file",
            str(action),
            "--allow-reference-authorization",
        )
        self.assertFalse(begun["reused"])
        self.assertEqual(1, begun["state_version"])

        repeated = self.run_statectl(
            "begin-action",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--action-file",
            str(action),
            "--allow-reference-authorization",
        )
        self.assertTrue(repeated["reused"])
        self.assertEqual(begun["action_id"], repeated["action_id"])

        conflicting = self.write_json(
            "conflicting-action.json",
            {
                **json.loads(action.read_text(encoding="utf-8")),
                "args": {"release": "2"},
            },
        )
        rejected = self.run_statectl_raw(
            "begin-action",
            "--store",
            str(self.store),
            "--expected-version",
            "1",
            "--action-file",
            str(conflicting),
            "--allow-reference-authorization",
        )
        self.assertEqual(2, rejected.returncode)
        self.assertIn("already bound to another request", rejected.stderr)

        receipt = self.write_json(
            "receipt.json",
            {
                "status": "succeeded",
                "idempotency_key": "deploy:release-1",
                "source_ref": "tool://deploy/receipt-1",
                "observed_at": "2026-09-01T00:01:00Z",
                "details": {"release": "1"},
            },
        )
        wrong_receipt = self.write_json(
            "wrong-receipt.json",
            {
                **json.loads(receipt.read_text(encoding="utf-8")),
                "idempotency_key": "deploy:another-release",
            },
        )
        rejected = self.run_statectl_raw(
            "resolve-action",
            "--store",
            str(self.store),
            "--expected-version",
            "1",
            "--action-id",
            begun["action_id"],
            "--outcome",
            "confirmed",
            "--receipt-file",
            str(wrong_receipt),
        )
        self.assertEqual(2, rejected.returncode)
        self.assertIn("idempotency key does not match", rejected.stderr)
        effect = self.write_json(
            "effect.json",
            [
                {
                    "op": "add",
                    "path": "/confirmed_facts/release",
                    "value": {
                        "value": "1",
                        "source_ref": "tool://deploy/receipt-1",
                        "observed_at": "2026-09-01T00:01:00Z",
                    },
                }
            ],
        )

        state = self.run_statectl(
            "resolve-action",
            "--store",
            str(self.store),
            "--expected-version",
            "1",
            "--action-id",
            begun["action_id"],
            "--outcome",
            "confirmed",
            "--receipt-file",
            str(receipt),
            "--patch-file",
            str(effect),
        )

        self.assertEqual(2, state["state_version"])
        self.assertEqual({}, state["pending_actions"])
        self.assertEqual("1", state["confirmed_facts"]["release"]["value"])

        repeated_resolution = self.run_statectl(
            "resolve-action",
            "--store",
            str(self.store),
            "--expected-version",
            "1",
            "--action-id",
            begun["action_id"],
            "--outcome",
            "confirmed",
            "--receipt-file",
            str(receipt),
            "--patch-file",
            str(effect),
        )
        self.assertEqual(2, repeated_resolution["state_version"])

    def test_failed_action_records_observed_failure(self) -> None:
        self.init_store()
        action = self.write_json(
            "action.json",
            {
                "idempotency_key": "publish:release-1",
                "tool": "publish",
                "args": {"release": "1"},
                "authorization_ref": "user-request://turn-1",
                "preconditions": [],
            },
        )
        begun = self.run_statectl(
            "begin-action",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--action-file",
            str(action),
            "--allow-reference-authorization",
        )
        receipt = self.write_json(
            "failure.json",
            {
                "status": "failed",
                "idempotency_key": "publish:release-1",
                "source_ref": "tool://publish/failure-1",
                "observed_at": "2026-09-01T00:02:00Z",
                "details": {"error": "permission denied"},
            },
        )

        state = self.run_statectl(
            "resolve-action",
            "--store",
            str(self.store),
            "--expected-version",
            "1",
            "--action-id",
            begun["action_id"],
            "--outcome",
            "failed",
            "--receipt-file",
            str(receipt),
        )

        self.assertEqual({}, state["pending_actions"])
        failure = state["failed_attempts"]["publish:release-1"]
        self.assertEqual(begun["action_id"], failure["action_id"])
        self.assertEqual("publish", failure["tool"])
        self.assertEqual("tool://publish/failure-1", failure["source_ref"])

    def test_action_preconditions_are_enforced_before_pending_commit(self) -> None:
        self.init_store()
        action = self.write_json(
            "blocked-action.json",
            {
                "idempotency_key": "deploy:blocked",
                "tool": "deploy",
                "args": {},
                "authorization_ref": "user-request://turn-1",
                "preconditions": [
                    {
                        "path": "/completion_evidence/tests-pass",
                        "operator": "exists",
                    }
                ],
            },
        )

        rejected = self.run_statectl_raw(
            "begin-action",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--action-file",
            str(action),
            "--allow-reference-authorization",
        )

        self.assertEqual(2, rejected.returncode)
        self.assertIn("action precondition[0] failed", rejected.stderr)
        state = self.run_statectl("show", "--store", str(self.store))
        self.assertEqual(0, state["state_version"])
        self.assertEqual({}, state["pending_actions"])

    def test_partial_action_stays_pending_until_late_success_receipt(self) -> None:
        self.init_store()
        action = self.write_json(
            "partial-action.json",
            {
                "idempotency_key": "deploy:partial",
                "tool": "deploy",
                "args": {"release": "1"},
                "authorization_ref": "user-request://turn-1",
                "preconditions": [],
            },
        )
        begun = self.run_statectl(
            "begin-action",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--action-file",
            str(action),
            "--allow-reference-authorization",
        )
        partial_receipt = self.write_json(
            "partial-receipt.json",
            {
                "status": "partial",
                "idempotency_key": "deploy:partial",
                "source_ref": "tool://deploy/partial-1",
                "observed_at": "2026-09-01T00:01:00Z",
                "details": {"external_id": "version-1"},
            },
        )
        partial_patch = self.write_json(
            "partial-effect.json",
            [
                {
                    "op": "add",
                    "path": "/confirmed_facts/external_id",
                    "value": {
                        "value": "version-1",
                        "source_ref": "tool://deploy/partial-1",
                        "observed_at": "2026-09-01T00:01:00Z",
                    },
                }
            ],
        )

        rejected = self.run_statectl_raw(
            "resolve-action",
            "--store",
            str(self.store),
            "--expected-version",
            "1",
            "--action-id",
            begun["action_id"],
            "--outcome",
            "failed",
            "--receipt-file",
            str(partial_receipt),
        )
        self.assertEqual(2, rejected.returncode)
        self.assertIn("failed outcome requires", rejected.stderr)

        pending = self.run_statectl(
            "resolve-action",
            "--store",
            str(self.store),
            "--expected-version",
            "1",
            "--action-id",
            begun["action_id"],
            "--outcome",
            "pending",
            "--receipt-file",
            str(partial_receipt),
            "--patch-file",
            str(partial_patch),
        )

        self.assertEqual(2, pending["state_version"])
        observation = pending["pending_actions"][begun["action_id"]][
            "last_observation"
        ]
        self.assertEqual("partial", observation["status"])
        replayed = self.run_statectl("replay", "--store", str(self.store))
        self.assertTrue(replayed["replayed"])
        self.assertEqual(3, replayed["event_count"])

        success_receipt = self.write_json(
            "late-success.json",
            {
                "status": "succeeded",
                "idempotency_key": "deploy:partial",
                "source_ref": "tool://deploy/success-1",
                "observed_at": "2026-09-01T00:02:00Z",
                "details": {"external_id": "version-1"},
            },
        )
        resolved = self.run_statectl(
            "resolve-action",
            "--store",
            str(self.store),
            "--expected-version",
            "2",
            "--action-id",
            begun["action_id"],
            "--outcome",
            "confirmed",
            "--receipt-file",
            str(success_receipt),
        )
        self.assertEqual({}, resolved["pending_actions"])
        self.assertEqual(3, resolved["state_version"])

        repeated = self.run_statectl(
            "resolve-action",
            "--store",
            str(self.store),
            "--expected-version",
            "2",
            "--action-id",
            begun["action_id"],
            "--outcome",
            "confirmed",
            "--receipt-file",
            str(success_receipt),
        )
        self.assertEqual(3, repeated["state_version"])

    def test_completion_requires_evidence_and_no_pending_action(self) -> None:
        self.init_store()
        rejected = self.run_statectl_raw(
            "complete",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
        )
        self.assertEqual(2, rejected.returncode)
        self.assertIn("cannot complete without evidence", rejected.stderr)

        evidence = self.write_json(
            "completion.json",
            [
                {
                    "op": "add",
                    "path": "/completion_evidence/tests-pass",
                    "value": {
                        "source_ref": "tool://tests/run-1",
                        "observed_at": "2026-09-01T00:03:00Z",
                    },
                }
            ],
        )
        self.run_statectl(
            "apply-patch",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--patch-file",
            str(evidence),
        )

        state = self.run_statectl(
            "complete",
            "--store",
            str(self.store),
            "--expected-version",
            "1",
        )

        self.assertEqual("complete", state["task"]["status"])
        self.assertEqual(2, state["state_version"])

        repeated = self.run_statectl(
            "complete",
            "--store",
            str(self.store),
            "--expected-version",
            "1",
        )
        self.assertEqual(2, repeated["state_version"])

        rejected = self.run_statectl_raw(
            "apply-patch",
            "--store",
            str(self.store),
            "--expected-version",
            "2",
            "--patch-file",
            str(evidence),
        )
        self.assertEqual(2, rejected.returncode)
        self.assertIn("task is complete", rejected.stderr)

        action = self.write_json(
            "post-completion-action.json",
            {
                "idempotency_key": "deploy:too-late",
                "tool": "deploy",
                "args": {},
                "authorization_ref": "user-request://turn-1",
                "preconditions": [],
            },
        )
        rejected = self.run_statectl_raw(
            "begin-action",
            "--store",
            str(self.store),
            "--expected-version",
            "2",
            "--action-file",
            str(action),
            "--allow-reference-authorization",
        )
        self.assertEqual(2, rejected.returncode)
        self.assertIn("task is complete", rejected.stderr)

    def test_concurrent_patches_do_not_silently_lose_an_update(self) -> None:
        self.init_store()
        first = self.write_json(
            "first.json",
            [{"op": "add", "path": "/plan/first", "value": {"status": "ready"}}],
        )
        second = self.write_json(
            "second.json",
            [
                {
                    "op": "add",
                    "path": "/plan/second",
                    "value": {"status": "ready"},
                }
            ],
        )
        processes = [
            subprocess.Popen(
                self.statectl_command(
                    "apply-patch",
                    "--store",
                    str(self.store),
                    "--expected-version",
                    "0",
                    "--patch-file",
                    str(patch),
                ),
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for patch in (first, second)
        ]
        results = [process.communicate(timeout=10) for process in processes]
        returncodes = sorted(process.returncode for process in processes)

        self.assertEqual([0, 2], returncodes, results)
        self.assertTrue(
            any("stale state version" in stderr for _, stderr in results),
            results,
        )
        state = self.run_statectl("show", "--store", str(self.store))
        self.assertEqual(1, state["state_version"])
        self.assertEqual(1, len(state["plan"]))

    def test_transaction_crash_rolls_back_and_missing_snapshot_recovers(self) -> None:
        self.init_store()
        crash = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import os, sqlite3, sys; "
                    "connection = sqlite3.connect(sys.argv[1], isolation_level=None); "
                    "connection.execute('BEGIN IMMEDIATE'); "
                    "connection.execute('UPDATE tasks SET state_version = 99'); "
                    "os._exit(17)"
                ),
                str(self.store / "state.db"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(17, crash.returncode)
        state = self.run_statectl("show", "--store", str(self.store))
        self.assertEqual(0, state["state_version"])

        (self.store / "state.snapshot.json").unlink()
        verified = self.run_statectl("verify", "--store", str(self.store))
        self.assertTrue(verified["verified"])
        self.assertTrue((self.store / "state.snapshot.json").is_file())

        snapshot = self.store / "state.snapshot.json"
        snapshot.chmod(0o600)
        snapshot.write_text("not json\n", encoding="utf-8")
        verified = self.run_statectl("verify", "--store", str(self.store))
        self.assertTrue(verified["verified"])
        self.assertEqual(
            0,
            json.loads(snapshot.read_text(encoding="utf-8"))["state_version"],
        )

    def test_fault_injection_distinguishes_precommit_rollback_from_postcommit_state(
        self,
    ) -> None:
        self.init_store()
        patch = self.write_json(
            "fault-patch.json",
            [{"op": "add", "path": "/plan/fault", "value": {"status": "ready"}}],
        )
        command = self.statectl_command(
            "apply-patch",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--patch-file",
            str(patch),
        )

        before_commit_env = os.environ.copy()
        before_commit_env["STATECTL_FAULT_POINT"] = "apply-patch.before-commit"
        before_commit = subprocess.run(
            command,
            cwd=ROOT,
            env=before_commit_env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(2, before_commit.returncode)
        self.assertIn("fault injected at apply-patch.before-commit", before_commit.stderr)
        self.assertEqual(
            0,
            self.run_statectl("show", "--store", str(self.store))["state_version"],
        )

        after_commit_env = os.environ.copy()
        after_commit_env["STATECTL_FAULT_POINT"] = "apply-patch.after-commit"
        after_commit = subprocess.run(
            command,
            cwd=ROOT,
            env=after_commit_env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(2, after_commit.returncode)
        self.assertIn("fault injected at apply-patch.after-commit", after_commit.stderr)
        state = self.run_statectl("show", "--store", str(self.store))
        self.assertEqual(1, state["state_version"])
        self.assertEqual("ready", state["plan"]["fault"]["status"])
        self.assertTrue(
            self.run_statectl("verify", "--store", str(self.store))["verified"]
        )

    def test_event_replay_detects_current_state_tampering(self) -> None:
        self.init_store()
        connection = sqlite3.connect(self.store / "state.db")
        try:
            state_text = connection.execute("SELECT state_json FROM tasks").fetchone()[0]
            state = json.loads(state_text)
            state["hypotheses"]["ghost"] = {"statement": "not in event ledger"}
            connection.execute(
                "UPDATE tasks SET state_json = ?",
                (json.dumps(state, separators=(",", ":"), sort_keys=True),),
            )
            connection.commit()
        finally:
            connection.close()

        rejected = self.run_statectl_raw("verify", "--store", str(self.store))
        self.assertEqual(2, rejected.returncode)
        self.assertIn("event replay differs", rejected.stderr)

    def test_event_replay_detects_action_table_tampering(self) -> None:
        self.init_store()
        action = self.write_json(
            "tamper-action.json",
            {
                "idempotency_key": "deploy:tamper",
                "tool": "deploy",
                "args": {},
                "authorization_ref": "user-request://turn-1",
                "preconditions": [],
            },
        )
        self.run_statectl(
            "begin-action",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--action-file",
            str(action),
            "--allow-reference-authorization",
        )
        connection = sqlite3.connect(self.store / "state.db")
        try:
            connection.execute(
                "UPDATE actions SET request_json = ?",
                (json.dumps({"tool": "other"}),),
            )
            connection.commit()
        finally:
            connection.close()

        rejected = self.run_statectl_raw("verify", "--store", str(self.store))
        self.assertEqual(2, rejected.returncode)
        self.assertIn("action table differs from event replay", rejected.stderr)

    def test_replay_rejects_authorization_evidence_not_bound_to_request(self) -> None:
        self.init_store()
        action = self.write_json(
            "authorization-tamper-action.json",
            {
                "idempotency_key": "deploy:authorization-tamper",
                "tool": "deploy",
                "args": {"release": "1"},
                "authorization_ref": "user-request://turn-1",
                "preconditions": [],
            },
        )
        begun = self.run_statectl(
            "begin-action",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--action-file",
            str(action),
            "--allow-reference-authorization",
        )
        connection = sqlite3.connect(self.store / "state.db")
        try:
            event_row = connection.execute(
                "SELECT sequence, payload_json FROM events WHERE kind = 'action-begun'"
            ).fetchone()
            event_payload = json.loads(event_row[1])
            event_payload["authorization_verification"]["request_sha256"] = "0" * 64
            connection.execute(
                "UPDATE events SET payload_json = ? WHERE sequence = ?",
                (
                    json.dumps(event_payload, separators=(",", ":"), sort_keys=True),
                    event_row[0],
                ),
            )
            state_text = connection.execute("SELECT state_json FROM tasks").fetchone()[0]
            state = json.loads(state_text)
            state["pending_actions"][begun["action_id"]][
                "authorization_verification"
            ]["request_sha256"] = "0" * 64
            connection.execute(
                "UPDATE tasks SET state_json = ?",
                (json.dumps(state, separators=(",", ":"), sort_keys=True),),
            )
            connection.commit()
        finally:
            connection.close()

        rejected = self.run_statectl_raw("verify", "--store", str(self.store))
        self.assertEqual(2, rejected.returncode)
        self.assertIn("authorization request hash does not match", rejected.stderr)

    def test_state_and_event_payload_budgets_are_enforced(self) -> None:
        self.run_statectl(
            "init",
            "--store",
            str(self.store),
            "--task-id",
            "release-1",
            "--objective",
            "Ship safely",
            "--criteria-file",
            str(self.criteria),
            "--max-state-bytes",
            "1024",
        )
        oversized = self.write_json(
            "oversized.json",
            [
                {
                    "op": "add",
                    "path": "/plan/oversized",
                    "value": "x" * 2000,
                }
            ],
        )
        rejected = self.run_statectl_raw(
            "apply-patch",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--patch-file",
            str(oversized),
        )
        self.assertEqual(2, rejected.returncode)
        self.assertIn("state size", rejected.stderr)
        self.assertEqual(
            0,
            self.run_statectl("show", "--store", str(self.store))["state_version"],
        )

        oversized_action = self.write_json(
            "oversized-action.json",
            {
                "idempotency_key": "deploy:oversized",
                "tool": "deploy",
                "args": {"raw_output": "x" * (65 * 1024)},
                "authorization_ref": "user-request://turn-1",
                "preconditions": [],
            },
        )
        rejected = self.run_statectl_raw(
            "begin-action",
            "--store",
            str(self.store),
            "--expected-version",
            "0",
            "--action-file",
            str(oversized_action),
            "--allow-reference-authorization",
        )
        self.assertEqual(2, rejected.returncode)
        self.assertIn("action request size", rejected.stderr)

    def test_public_schemas_stay_aligned_with_runtime_constants(self) -> None:
        runtime = runpy.run_path(str(STATECTL))
        schemas = STATECTL.parents[1] / "references" / "schemas"
        state_schema = json.loads(
            (schemas / "state.schema.json").read_text(encoding="utf-8")
        )
        action_schema = json.loads(
            (schemas / "action.schema.json").read_text(encoding="utf-8")
        )
        receipt_schema = json.loads(
            (schemas / "receipt.schema.json").read_text(encoding="utf-8")
        )
        patch_schema = json.loads(
            (schemas / "patch.schema.json").read_text(encoding="utf-8")
        )

        self.assertEqual(runtime["STATE_KEYS"], set(state_schema["required"]))
        self.assertEqual(runtime["ACTION_KEYS"], set(action_schema["required"]))
        self.assertEqual(runtime["RECEIPT_KEYS"], set(receipt_schema["required"]))
        self.assertEqual(
            runtime["RECEIPT_STATUSES"],
            set(receipt_schema["properties"]["status"]["enum"]),
        )
        self.assertEqual(
            runtime["PATCH_OPERATIONS"],
            set(patch_schema["items"]["properties"]["op"]["enum"]),
        )
        self.assertEqual(
            ["value"],
            patch_schema["items"]["allOf"][0]["else"]["not"]["required"],
        )
        self.assertEqual(
            runtime["PRECONDITION_OPERATORS"],
            set(
                action_schema["properties"]["preconditions"]["items"][
                    "properties"
                ]["operator"]["enum"]
            ),
        )

    def test_workspace_fixture_matches_exact_statectl_mutations(self) -> None:
        case = (
            ROOT
            / "evals"
            / "workspaces"
            / "durable-execution-state"
            / "statectl-workspace-init"
        )
        workspace = self.root / "workspace"
        shutil.copytree(case / "input", workspace)
        before = {
            path.relative_to(workspace).as_posix()
            for path in workspace.rglob("*")
        }
        before_files = {
            path.relative_to(workspace).as_posix(): path.read_bytes()
            for path in workspace.rglob("*")
            if path.is_file()
        }
        store = workspace / "work" / "agent-state" / "release-1"
        commands = [
            self.statectl_command(
                "init",
                "--store",
                str(store),
                "--task-id",
                "release-1",
                "--objective",
                "Ship safely",
                "--criteria-file",
                str(workspace / "criteria.json"),
            ),
            self.statectl_command(
                "apply-patch",
                "--store",
                str(store),
                "--expected-version",
                "0",
                "--patch-file",
                str(workspace / "patch.json"),
            ),
            self.statectl_command("verify", "--store", str(store)),
        ]
        outputs = [
            subprocess.run(
                command,
                cwd=workspace,
                capture_output=True,
                text=True,
                check=False,
            )
            for command in commands
        ]
        self.assertTrue(
            all(output.returncode == 0 for output in outputs),
            [(output.stdout, output.stderr) for output in outputs],
        )
        after = {
            path.relative_to(workspace).as_posix()
            for path in workspace.rglob("*")
        }
        expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
        actual_created = after - before
        required_created = set(expected["changes"]["created"])
        optional_created = set(expected.get("optional_created", []))
        self.assertTrue(
            required_created <= actual_created <= required_created | optional_created,
            sorted(actual_created),
        )
        self.assertEqual(
            before_files,
            {
                path.relative_to(workspace).as_posix(): path.read_bytes()
                for path in workspace.rglob("*")
                if path.is_file()
                and path.relative_to(workspace).as_posix() in before_files
            },
        )
        self.assertEqual([], expected["changes"]["modified"])
        self.assertEqual([], expected["changes"]["deleted"])

    def init_store(self) -> dict[str, object]:
        return self.run_statectl(
            "init",
            "--store",
            str(self.store),
            "--task-id",
            "release-1",
            "--objective",
            "Ship safely",
            "--criteria-file",
            str(self.criteria),
        )

    def write_json(self, name: str, value: object) -> Path:
        path = self.root / name
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def run_statectl(self, *arguments: str) -> dict[str, object]:
        completed = self.run_statectl_raw(*arguments)
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertIsInstance(result, dict)
        return result

    @staticmethod
    def run_statectl_raw(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            DurableExecutionStateTest.statectl_command(*arguments),
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    @staticmethod
    def statectl_command(*arguments: str) -> list[str]:
        return [sys.executable, str(STATECTL), *arguments]


if __name__ == "__main__":
    unittest.main()
