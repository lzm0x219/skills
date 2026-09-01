from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import stat
import subprocess
from typing import Any

from .codec import canonical_json, parse_rfc3339, validate_rfc3339 as validate_timestamp
from .errors import StateError


MAX_VERIFIER_RESPONSE_BYTES = 64 * 1024
VERIFIER_RESPONSE_KEYS = {
    "authorized",
    "authorization_ref",
    "request_sha256",
    "verifier_ref",
    "verified_at",
}


def request_sha256(request: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(request).encode("utf-8")).hexdigest()


def reference_authorization(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": "reference-only",
        "authorization_ref": request["authorization_ref"],
        "request_sha256": request_sha256(request),
        "verifier_ref": "unverified://explicit-downgrade",
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_recorded_authorization(
    value: object,
    request: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StateError("authorization verification must be an object")
    required_keys = {
        "mode",
        "authorization_ref",
        "request_sha256",
        "verifier_ref",
        "verified_at",
    }
    allowed_keys = required_keys | {"expires_at"}
    if set(value) < required_keys or not set(value) <= allowed_keys:
        raise StateError(
            "authorization verification keys must include "
            f"{sorted(required_keys)} and optional expires_at"
        )
    if value["mode"] not in {"trusted-verifier", "reference-only"}:
        raise StateError("authorization verification mode is invalid")
    authorization_ref = value["authorization_ref"]
    if not isinstance(authorization_ref, str) or not hmac.compare_digest(
        authorization_ref, request["authorization_ref"]
    ):
        raise StateError("authorization reference does not match the request")
    digest = value["request_sha256"]
    if not isinstance(digest, str) or not hmac.compare_digest(
        digest, request_sha256(request)
    ):
        raise StateError("authorization request hash does not match")
    verifier_ref = value["verifier_ref"]
    if not isinstance(verifier_ref, str) or not verifier_ref.strip():
        raise StateError("authorization verifier_ref must be a non-empty string")
    if (
        value["mode"] == "reference-only"
        and verifier_ref != "unverified://explicit-downgrade"
    ):
        raise StateError("reference-only authorization must use the downgrade marker")
    verified_at = validate_timestamp(value["verified_at"], "verified_at")
    if "expires_at" in value:
        expires_at = validate_timestamp(value["expires_at"], "expires_at")
        parsed_verified = parse_rfc3339(verified_at, "verified_at")
        parsed_expiry = parse_rfc3339(expires_at, "expires_at")
        if parsed_expiry <= parsed_verified:
            raise StateError("authorization expiry must be after verification time")
    return value


def _validated_verifier_path(value: str, store: Path) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        raise StateError("authorization verifier path must be absolute")
    verifier = candidate.resolve()
    if not verifier.is_file() or not os.access(verifier, os.X_OK):
        raise StateError(f"authorization verifier is not executable: {verifier}")
    try:
        verifier.relative_to(store.resolve())
    except ValueError:
        pass
    else:
        raise StateError("authorization verifier must be outside the mutable state store")
    if verifier.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise StateError("authorization verifier must not be group- or world-writable")
    return verifier


def _parse_verifier_response(
    stdout: str,
    request: dict[str, Any],
    digest: str,
) -> dict[str, Any]:
    if len(stdout.encode("utf-8")) > MAX_VERIFIER_RESPONSE_BYTES:
        raise StateError("authorization verifier response exceeds 65536 bytes")
    try:
        response = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise StateError("authorization verifier returned invalid JSON") from error
    if not isinstance(response, dict):
        raise StateError("authorization verifier response must be an object")
    allowed_keys = VERIFIER_RESPONSE_KEYS | {"expires_at"}
    if set(response) < VERIFIER_RESPONSE_KEYS or not set(response) <= allowed_keys:
        raise StateError(
            "authorization verifier response keys must include "
            f"{sorted(VERIFIER_RESPONSE_KEYS)} and optional expires_at"
        )
    if response["authorized"] is not True:
        raise StateError("authorization verifier denied the action")
    authorization_ref = response["authorization_ref"]
    if not isinstance(authorization_ref, str):
        raise StateError("authorization verifier authorization_ref must be a string")
    if not hmac.compare_digest(authorization_ref, request["authorization_ref"]):
        raise StateError("authorization reference does not match the request")
    response_digest = response["request_sha256"]
    if not isinstance(response_digest, str):
        raise StateError("authorization verifier request_sha256 must be a string")
    if not hmac.compare_digest(response_digest, digest):
        raise StateError("authorization verifier request hash does not match")
    verifier_ref = response["verifier_ref"]
    if not isinstance(verifier_ref, str) or not verifier_ref.strip():
        raise StateError("authorization verifier_ref must be a non-empty string")
    verified_at = validate_timestamp(response["verified_at"], "verified_at")
    result = {
        "mode": "trusted-verifier",
        "authorization_ref": request["authorization_ref"],
        "request_sha256": digest,
        "verifier_ref": verifier_ref,
        "verified_at": verified_at,
    }
    if "expires_at" in response:
        expires_at = validate_timestamp(response["expires_at"], "expires_at")
        parsed_expiry = parse_rfc3339(expires_at, "expires_at")
        if parsed_expiry <= datetime.now(timezone.utc):
            raise StateError("authorization verifier response is expired")
        result["expires_at"] = expires_at
    return result


def verify_authorization(
    request: dict[str, Any],
    *,
    store: Path,
    verifier_path: str | None,
    allow_reference: bool,
) -> dict[str, Any]:
    if allow_reference:
        return validate_recorded_authorization(reference_authorization(request), request)
    if verifier_path is None:
        raise StateError(
            "trusted authorization verifier is required; statectl path checks do not "
            "establish host trust, so the host must pin --authorization-verifier; "
            "otherwise explicitly use "
            "--allow-reference-authorization only for rehearsal/tests"
        )
    verifier = _validated_verifier_path(verifier_path, store)
    digest = request_sha256(request)
    payload = canonical_json({"request": request, "request_sha256": digest})
    try:
        completed = subprocess.run(
            [str(verifier)],
            input=payload,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
            env={"LANG": "C.UTF-8", "PATH": os.defpath},
        )
    except subprocess.TimeoutExpired as error:
        raise StateError("authorization verifier timed out") from error
    except OSError as error:
        raise StateError(f"authorization verifier could not run: {error}") from error
    if completed.returncode != 0:
        detail = completed.stderr.strip()[:1000]
        suffix = f": {detail}" if detail else ""
        raise StateError(
            f"authorization verifier exited with {completed.returncode}{suffix}"
        )
    return validate_recorded_authorization(
        _parse_verifier_response(completed.stdout, request, digest),
        request,
    )
