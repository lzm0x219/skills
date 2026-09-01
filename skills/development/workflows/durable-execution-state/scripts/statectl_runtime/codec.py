from __future__ import annotations

from datetime import datetime
import json
import re

from .errors import StateError


_RFC3339_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}"
    r"(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})$"
)


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def json_size(value: object) -> int:
    return len(canonical_json(value).encode("utf-8"))


def parse_rfc3339(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not _RFC3339_TIMESTAMP.fullmatch(value):
        raise StateError(f"{label} must be an RFC 3339 timestamp")
    normalized = value.replace("t", "T", 1)
    if normalized.endswith(("Z", "z")):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as error:
        raise StateError(f"{label} must be an RFC 3339 timestamp") from error


def validate_rfc3339(value: object, label: str) -> str:
    parse_rfc3339(value, label)
    assert isinstance(value, str)
    return value
