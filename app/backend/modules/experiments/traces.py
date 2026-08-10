import json
import re
from typing import Any

HEADER = re.compile(r"^---- (?P<timestamp>\S+) (?P<segment>.+) ----$")


def parse_coverup_log(value: str) -> list[dict[str, Any]]:
    """Convert CoverUp's framed JSON log into stable request/response trace events."""
    events: list[dict[str, Any]] = []
    timestamp = ""
    segment = ""
    buffer: list[str] = []

    def flush() -> None:
        if not buffer:
            return
        try:
            payload = json.loads("\n".join(buffer))
        except json.JSONDecodeError:
            buffer.clear()
            return
        kind = "response" if isinstance(payload, dict) and "choices" in payload else "request"
        events.append({"timestamp": timestamp, "segment": segment, "kind": kind, "payload": payload})
        buffer.clear()

    for line in value.splitlines():
        match = HEADER.match(line)
        if match:
            flush()
            timestamp = match.group("timestamp")
            segment = match.group("segment")
        else:
            buffer.append(line)
    flush()
    return events


def as_jsonl(events: list[dict[str, Any]]) -> bytes:
    return ("\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n").encode()
