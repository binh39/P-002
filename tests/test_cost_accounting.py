from src.optimization.costs import aggregate_usage_events, estimate_cost, normalize_usage, usage_event


def test_normalize_usage_supports_openai_and_gemini_field_names():
    assert normalize_usage({"prompt_tokens": 12, "completion_tokens": 3}) == {
        "prompt_tokens": 12,
        "completion_tokens": 3,
        "total_tokens": 15,
    }
    assert normalize_usage({"input_tokens": 7, "output_tokens": 2, "cached_tokens": 4}) == {
        "prompt_tokens": 7,
        "completion_tokens": 2,
        "cache_read_input_tokens": 4,
        "total_tokens": 9,
    }


def test_cost_estimates_all_configured_provider_families_from_pinned_price_map():
    usage = {"prompt_tokens": 1_000, "completion_tokens": 100}
    for model in (
        "openai/gpt-4.1-mini",
        "deepseek/deepseek-v4-flash",
        "gemini/gemini-2.5-flash-lite",
        "vertex_ai/gemini-3.5-flash-lite",
    ):
        cost = estimate_cost(model, usage)
        assert cost is not None
        assert cost > 0


def test_aggregate_usage_deduplicates_requests_and_keeps_unpriced_usage_visible():
    priced = usage_event(
        "openai/gpt-4.1-mini",
        {"prompt_tokens": 10, "completion_tokens": 5},
        response_cost=0.25,
        event_id="one",
    )
    unpriced = usage_event(
        "unknown/provider",
        {"prompt_tokens": 9, "completion_tokens": 1},
        event_id="two",
    )
    report = aggregate_usage_events([priced, priced, unpriced])

    assert report["estimated_cost_usd"] == 0.25
    assert report["priced_request_count"] == 1
    assert report["unpriced_request_count"] == 1
    assert report["token_usage"]["prompt_tokens"] == 19
