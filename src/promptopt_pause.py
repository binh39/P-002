"""Cooperative pause signalling shared by model workers and the job wrapper."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

PAUSE_FILE_ENV = "PROMPTOPT_PAUSE_FILE"
RATE_LIMIT_THRESHOLD_ENV = "PROMPTOPT_PAUSE_AFTER_429"
DEFAULT_RATE_LIMIT_THRESHOLD = 5


class ModelRateLimitPauseError(RuntimeError):
    """Raised after a durable pause request has been written for repeated 429s."""


def pause_file() -> Path | None:
    value = os.environ.get(PAUSE_FILE_ENV, "").strip()
    return Path(value).resolve() if value else None


def rate_limit_pause_threshold() -> int:
    raw = os.environ.get(RATE_LIMIT_THRESHOLD_ENV, "").strip()
    if not raw:
        return DEFAULT_RATE_LIMIT_THRESHOLD
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_RATE_LIMIT_THRESHOLD


def request_rate_limit_pause(
    *,
    model: str,
    attempt: int,
    error: BaseException,
    force: bool = False,
) -> bool:
    """Atomically request a pause when this job has a configured signal file."""
    destination = pause_file()
    if destination is None or (not force and attempt < rate_limit_pause_threshold()):
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "reason": "rate_limited",
        "status_code": 429,
        "model": model,
        "attempt": attempt,
        "message": " ".join(str(error).split())[:2000],
        "requested_at": datetime.now(UTC).isoformat(),
    }
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(temporary, destination)
    return True


def read_pause_request(path: Path | None = None) -> dict[str, Any] | None:
    source = path or pause_file()
    if source is None or not source.is_file():
        return None
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None
