# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args
from isort.wrap_modes import WrapModes


def test_parse_args_deprecated_args():
    # Test DEPRECATED_SINGLE_DASH_ARGS remapping (lines 931-934, 938-939)
    # Using one of the deprecated single dash args, e.g., "-ac" without leading hyphen in list if stored as such,
    # or let's check DEPRECATED_SINGLE_DASH_ARGS contents. They include things like 'ac' or '-ac'.
    # Let's check what DEPRECATED_SINGLE_DASH_ARGS contains.
    from isort.main import DEPRECATED_SINGLE_DASH_ARGS
    # Pick one item from DEPRECATED_SINGLE_DASH_ARGS
    arg = next(iter(DEPRECATED_SINGLE_DASH_ARGS))
    # If the set contains items with or without leading hyphen:
    # Let's inspect or just pass a dummy valid flag or test with whatever is in DEPRECATED_SINGLE_DASH_ARGS
    parsed = parse_args([arg, "."])
    assert "remapped_deprecated_args" in parsed


def test_parse_args_dont_order_by_type():
    # Test dont_order_by_type (lines 940-942)
    parsed = parse_args(["--dont-order-by-type", "."])
    assert parsed.get("order_by_type") is False
    assert "dont_order_by_type" not in parsed


def test_parse_args_dont_follow_links():
    # Test dont_follow_links (lines 943-945)
    parsed = parse_args(["--dont-follow-links", "."])
    assert parsed.get("follow_links") is False
    assert "dont_follow_links" not in parsed


def test_parse_args_dont_float_to_top_else():
    # Test dont_float_to_top when float_to_top is not set (lines 946-951, else branch)
    parsed = parse_args(["--dont-float-to-top", "."])
    assert parsed.get("float_to_top") is False
    assert "dont_float_to_top" not in parsed


def test_parse_args_dont_float_to_top_conflict():
    # Test dont_float_to_top when float_to_top is also set (lines 948-949, sys.exit)
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--float-to-top", "--dont-float-to-top", "."])
    assert "Can't set both" in str(exc_info.value)


def test_parse_args_multi_line_output_digit():
    # Test multi_line_output as digit (lines 953-955)
    parsed = parse_args(["--multi-line", "3", "."])
    assert parsed.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT


def test_parse_args_multi_line_output_name():
    # Test multi_line_output as string name (lines 956-957)
    parsed = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT", "."])
    assert parsed.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT
