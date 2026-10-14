"""Append one bounded, reviewable JSON record for every agent-loop event."""

from __future__ import annotations

import fcntl
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = PROJECT_ROOT / "output" / "audit_trail.json"
_WRITE_LOCK = threading.Lock()
MAX_FIELD_CHARS = 1400


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def clip(value: Any, limit: int = MAX_FIELD_CHARS) -> str:
    text = value if isinstance(value, str) else str(value)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _bounded(value: Any) -> Any:
    if isinstance(value, str):
        return clip(value)
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, list):
        return [_bounded(item) for item in value[:20]]
    if isinstance(value, dict):
        return {str(key)[:80]: _bounded(item) for key, item in list(value.items())[:30]}
    return clip(value)


def _append_json_array_record(record: dict[str, Any]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(AUDIT_PATH, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        with _WRITE_LOCK:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            with os.fdopen(descriptor, "r+b", closefd=False) as trail:
                trail.seek(0)
                raw = trail.read()
                if raw.strip():
                    existing = json.loads(raw.decode("utf-8"))
                    if not isinstance(existing, list) or any(not isinstance(item, dict) for item in existing):
                        raise ValueError("The audit trail must be a JSON array of records.")
                else:
                    existing = []
                    raw = b"[\n]\n"
                    trail.seek(0)
                    trail.write(raw)
                    trail.flush()

                closing = raw.rstrip().rfind(b"]")
                if closing < 0:
                    raise ValueError("The audit trail JSON array is incomplete.")
                prefix = raw[:closing].rstrip()
                trail.seek(len(prefix))
                trail.truncate()
                trail.write(b",\n  " if existing else b"\n  ")
                encoded = json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                trail.write(encoded)
                trail.write(b"\n]\n")
                trail.flush()
                os.fsync(descriptor)
            os.chmod(AUDIT_PATH, 0o600)
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


class AuditTrail:
    """Persist each event immediately without replacing earlier run records."""

    def record(self, **fields: Any) -> None:
        record = {"time": utc_now()}
        for name, value in fields.items():
            record[name] = _bounded(value)
        _append_json_array_record(record)
