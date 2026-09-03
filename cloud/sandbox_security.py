"""Security helpers shared by sandbox build and execution diagnostics."""

from __future__ import annotations

import re
from collections.abc import Iterable

REDACTED = "<redacted>"

_URL_CREDENTIALS = re.compile(r"(?i)(https?://)([^/@\s:]+):([^/@\s]+)@")
_AUTH_HEADER = re.compile(r"(?im)\b(authorization\s*[:=]\s*)(?:bearer|basic)\s+[^\s,;]+")
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b([A-Z0-9_.-]*(?:TOKEN|API[_-]?KEY|SECRET|PASSWORD|PASSWD|CREDENTIAL)[A-Z0-9_.-]*)"
    r"(\s*[:=]\s*)([^\s,;]+)"
)
_SIGNED_QUERY = re.compile(
    r"(?i)([?&](?:access_token|api_key|key|signature|sig|token|x-amz-signature|x-goog-signature)=)"
    r"([^&#\s]+)"
)


def redact_sensitive_text(value: str, *, secrets: Iterable[str] = ()) -> str:
    """Remove credential-shaped values without hiding useful diagnostics."""

    text = value
    for secret in sorted((item for item in secrets if item), key=len, reverse=True):
        text = text.replace(secret, REDACTED)
    text = _URL_CREDENTIALS.sub(r"\1" + REDACTED + "@", text)
    text = _AUTH_HEADER.sub(r"\1" + REDACTED, text)
    text = _SECRET_ASSIGNMENT.sub(r"\1\2" + REDACTED, text)
    return _SIGNED_QUERY.sub(r"\1" + REDACTED, text)


def bounded_redacted_text(value: str, maximum_bytes: int, *, secrets: Iterable[str] = ()) -> str:
    """Redact first, then enforce a UTF-8 byte limit on a diagnostic."""

    if maximum_bytes <= 0:
        return ""
    redacted = redact_sensitive_text(value, secrets=secrets)
    encoded = redacted.encode("utf-8")
    if len(encoded) <= maximum_bytes:
        return redacted
    suffix = b"\n<output truncated by sandbox>"
    available = max(0, maximum_bytes - len(suffix))
    prefix = encoded[:available].decode("utf-8", errors="ignore")
    remaining = maximum_bytes - len(prefix.encode("utf-8"))
    return prefix + suffix[:remaining].decode("utf-8", errors="ignore")
