# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
import sys
from isort.main import parse_args
from isort.wrap_modes import WrapModes


def test_parse_args_default():
    # Test argv is None using sys.argv patching
    old_argv = sys.argv
    try:
        sys.argv = ["isort"]
        result = parse_args()
        assert isinstance(result, dict)
    finally:
        sys.argv = old_argv


def test_parse_args_deprecated_single_dash_args():
    # DEPRECATED_SINGLE_DASH_ARGS items have a leading dash in the set, e.g. '-ac'.
    # When passed on CLI with single dash like '-ac', parse_args remaps it.
    result = parse_args(["-ac"])
    assert "remapped_deprecated_args" in result
    assert result["remapped_deprecated_args"] == ["-ac"]


def test_parse_args_dont_order_by_type():
    result = parse_args(["--dont-order-by-type"])
    assert result.get("order_by_type") is False
    assert "dont_order_by_type" not in result


def test_parse_args_dont_follow_links():
    result = parse_args(["--dont-follow-links"])
    assert result.get("follow_links") is False
    assert "dont_follow_links" not in result


def test_parse_args_dont_float_to_top_conflict():
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--float-to-top", "--dont-float-to-top"])
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(exc_info.value)


def test_parse_args_dont_float_to_top_no_conflict():
    result = parse_args(["--dont-float-to-top"])
    assert result.get("float_to_top") is False
    assert "dont_float_to_top" not in result


def test_parse_args_multi_line_output_digit():
    result = parse_args(["--multi-line", "3"])
    assert result.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT


def test_parse_args_multi_line_output_string():
    result = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT"])
    assert result.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT
