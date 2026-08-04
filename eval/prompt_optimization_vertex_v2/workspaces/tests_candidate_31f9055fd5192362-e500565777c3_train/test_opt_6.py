# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
import sys
from isort.main import parse_args
from isort.wrap_modes import WrapModes


def test_parse_args_deprecated_single_dash():
    # Test deprecated single dash args (e.g. ones in DEPRECATED_SINGLE_DASH_ARGS without the leading single dash in input, or with)
    # Looking at DEPRECATED_SINGLE_DASH_ARGS, elements start with '-' like '-ac'.
    # If arg is in DEPRECATED_SINGLE_DASH_ARGS, e.g. '-ac', it remapped.
    # Wait, if arg is in DEPRECATED_SINGLE_DASH_ARGS, it checks `arg in DEPRECATED_SINGLE_DASH_ARGS`.
    # Let's pick one from DEPRECATED_SINGLE_DASH_ARGS, e.g., '-ac'.
    args = ["-ac"]
    res = parse_args(args)
    assert "remapped_deprecated_args" in res
    assert "-ac" in res["remapped_deprecated_args"]


def test_parse_args_dont_order_by_type():
    res = parse_args(["--dont-order-by-type"])
    assert res.get("order_by_type") is False
    assert "dont_order_by_type" not in res


def test_parse_args_dont_follow_links():
    res = parse_args(["--dont-follow-links"])
    assert res.get("follow_links") is False
    assert "dont_follow_links" not in res


def test_parse_args_dont_float_to_top_false_case():
    res = parse_args(["--dont-float-to-top"])
    assert res.get("float_to_top") is False
    assert "dont_float_to_top" not in res


def test_parse_args_dont_float_to_top_conflict():
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["--float-to-top", "--dont-float-to-top"])
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(excinfo.value)


def test_parse_args_multi_line_output_digit():
    res = parse_args(["--multi-line", "3"])
    assert res.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT


def test_parse_args_multi_line_output_string():
    res = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT"])
    assert res.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT
