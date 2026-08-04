# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
import sys
from isort.main import parse_args
from isort.wrap_modes import WrapModes


def test_parse_args_deprecated_single_dash():
    # Test line 932: arg in DEPRECATED_SINGLE_DASH_ARGS
    # Let's find one, e.g. '-ac' without leading dash in DEPRECATED_SINGLE_DASH_ARGS or with single dash
    # Wait, DEPRECATED_SINGLE_DASH_ARGS values in isort usually have single dash or double dash? Let's check what DEPRECATED_SINGLE_DASH_ARGS contains.
    # Ah, DEPRECATED_SINGLE_DASH_ARGS keys usually don't have leading dashes or do they? Let's check.
    # Actually, we can pass any valid deprecated arg if we know it, or check DEPRECATED_SINGLE_DASH_ARGS directly.
    from isort.main import DEPRECATED_SINGLE_DASH_ARGS
    if DEPRECATED_SINGLE_DASH_ARGS:
        sample_arg = next(iter(DEPRECATED_SINGLE_DASH_ARGS))
        res = parse_args([sample_arg, "--version"]) # or similar
        assert "remapped_deprecated_args" in res


def test_parse_args_dont_order_and_follow_links():
    res = parse_args(["--dont-order-by-type", "--dont-follow-links"])
    assert res.get("order_by_type") is False
    assert res.get("follow_links") is False
    assert "dont_order_by_type" not in res
    assert "dont_follow_links" not in res


def test_parse_args_dont_float_to_top_else():
    res = parse_args(["--dont-float-to-top"])
    assert res.get("float_to_top") is False
    assert "dont_float_to_top" not in res


def test_parse_args_conflict_float_to_top():
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["--float-to-top", "--dont-float-to-top"])
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(excinfo.value)


def test_parse_args_multi_line_output_digit():
    res = parse_args(["--multi-line", "3"])
    assert isinstance(res.get("multi_line_output"), WrapModes)


def test_parse_args_multi_line_output_name():
    res = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT"])
    assert isinstance(res.get("multi_line_output"), WrapModes)
    assert res["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT
