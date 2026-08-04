from __future__ import annotations

from contextlib import nullcontext
from typing import Any


def experiment_span(name: str, metadata: dict[str, Any] | None = None):
    """Return a Langfuse span when configured, otherwise a safe no-op context."""
    try:
        from langfuse import get_client
    except ImportError:
        return nullcontext()
    client = get_client()
    return client.start_as_current_span(name=name, metadata=metadata or {})
