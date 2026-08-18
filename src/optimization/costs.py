"""Usage-based, provider-neutral cost accounting for PromptOpt runs.

Amounts are estimates derived from the exact usage returned by the provider and
the pinned LiteLLM price map.  They intentionally do not claim to be invoice
totals: Cloud Billing discounts, Vertex provisioned throughput, taxes and
provider-side rounding are outside a response-level trace.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

_USAGE_KEYS = {
    "prompt_tokens": ("prompt_tokens", "input_tokens"),
    "completion_tokens": ("completion_tokens", "output_tokens"),
    "total_tokens": ("total_tokens",),
    "cache_read_input_tokens": (
        "cache_read_input_tokens",
        "cached_tokens",
        "cache_read_tokens",
    ),
    "reasoning_tokens": ("reasoning_tokens",),
}


def normalize_usage(value: object) -> dict[str, int]:
    """Normalize OpenAI-compatible and Gemini/Vertex token field names."""
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, int] = {}
    for output_key, input_keys in _USAGE_KEYS.items():
        for input_key in input_keys:
            raw = value.get(input_key)
            try:
                number = int(raw)
            except (TypeError, ValueError):
                continue
            if number >= 0:
                result[output_key] = number
                break
    if "total_tokens" not in result and {"prompt_tokens", "completion_tokens"} <= result.keys():
        result["total_tokens"] = result["prompt_tokens"] + result["completion_tokens"]
    return result


def estimate_cost(model: str, usage: object, *, response_cost: object = None) -> float | None:
    """Prefer LiteLLM's response cost, then safely calculate its normal token tariff."""
    try:
        reported = float(response_cost)
    except (TypeError, ValueError):
        reported = None
    if reported is not None and reported >= 0:
        return reported
    normalized = normalize_usage(usage)
    if not {"prompt_tokens", "completion_tokens"} <= normalized.keys():
        return None
    try:
        import litellm

        pricing = litellm.model_cost.get(model) or litellm.model_cost.get(model.split("/", 1)[-1])
    except Exception:  # Cost accounting must never fail a test-generation run.
        return None
    if not isinstance(pricing, Mapping):
        return None
    try:
        prompt_tokens = normalized["prompt_tokens"]
        cached_tokens = min(normalized.get("cache_read_input_tokens", 0), prompt_tokens)
        uncached_tokens = prompt_tokens - cached_tokens
        input_cost = float(pricing["input_cost_per_token"])
        output_cost = float(pricing["output_cost_per_token"])
        cache_cost = float(pricing.get("cache_read_input_token_cost", input_cost))
    except (KeyError, TypeError, ValueError):
        return None
    return uncached_tokens * input_cost + cached_tokens * cache_cost + normalized["completion_tokens"] * output_cost


def usage_event(model: str, usage: object, *, response_cost: object = None, event_id: str = "") -> dict[str, Any]:
    normalized = normalize_usage(usage)
    return {
        "event": "llm_usage",
        "event_id": event_id,
        "model": model,
        "usage": normalized,
        "estimated_cost_usd": estimate_cost(model, normalized, response_cost=response_cost),
    }


def aggregate_usage_events(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate deduplicated request events without treating missing pricing as free."""
    seen: set[str] = set()
    usage_totals: dict[str, int] = defaultdict(int)
    by_model: dict[str, dict[str, Any]] = {}
    priced = unpriced = 0
    cost = 0.0
    for index, event in enumerate(events):
        if event.get("event") != "llm_usage":
            continue
        event_id = str(event.get("event_id") or f"row-{index}")
        if event_id in seen:
            continue
        seen.add(event_id)
        model = str(event.get("model") or "unknown")
        normalized = normalize_usage(event.get("usage"))
        for key, value in normalized.items():
            usage_totals[key] += value
        per_model = by_model.setdefault(
            model,
            {"estimated_cost_usd": 0.0, "priced_request_count": 0, "unpriced_request_count": 0, "token_usage": {}},
        )
        model_usage = per_model["token_usage"]
        for key, value in normalized.items():
            model_usage[key] = int(model_usage.get(key, 0)) + value
        try:
            request_cost = float(event.get("estimated_cost_usd"))
        except (TypeError, ValueError):
            request_cost = None
        if request_cost is None or request_cost < 0:
            unpriced += 1
            per_model["unpriced_request_count"] += 1
        else:
            cost += request_cost
            priced += 1
            per_model["estimated_cost_usd"] += request_cost
            per_model["priced_request_count"] += 1
    return {
        "estimated_cost_usd": cost,
        "token_usage": dict(usage_totals),
        "priced_request_count": priced,
        "unpriced_request_count": unpriced,
        "by_model": by_model,
    }


def cached_coverup_usage_events(candidate_dir: Path) -> list[dict[str, Any]]:
    """Read only cache evidence, never raw prompt/output text, from GEPA evaluations."""
    events: list[dict[str, Any]] = []
    for path in candidate_dir.glob("evaluations/**/*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        prompt_digest = str(payload.get("prompt_digest") or "")
        for result in payload.get("results", []):
            for event in result.get("attempt_traces", []):
                if isinstance(event, dict) and event.get("event") == "llm_usage":
                    events.append({**event, "prompt_digest": prompt_digest})
    return events


def dspy_usage_events(history: object) -> list[dict[str, Any]]:
    """Extract usage/cost from DSPy's sanitized LM history entries."""
    if not isinstance(history, list):
        return []
    events = []
    for index, entry in enumerate(history):
        if not isinstance(entry, Mapping):
            continue
        events.append(
            usage_event(
                str(entry.get("model") or "unknown"),
                entry.get("usage"),
                response_cost=entry.get("cost"),
                event_id=str(entry.get("uuid") or f"dspy-{index}"),
            )
        )
    return events


def build_cost_report(candidate_dir: Path, *, dspy_history: object = None) -> dict[str, Any]:
    coverup_events = cached_coverup_usage_events(candidate_dir)
    optimizer_events = dspy_usage_events(dspy_history)
    coverup = aggregate_usage_events(coverup_events)
    optimizer = aggregate_usage_events(optimizer_events)
    total = aggregate_usage_events([
        *coverup_events,
        *optimizer_events,
    ])
    by_prompt: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in coverup_events:
        by_prompt[str(event.get("prompt_digest") or "unknown")].append(event)
    return {
        "schema_version": 1,
        "coverup": coverup,
        "coverup_by_prompt": {digest: aggregate_usage_events(events) for digest, events in by_prompt.items()},
        "optimizer": optimizer,
        "total": total,
    }
