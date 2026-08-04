# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
import sys
from isort.main import parse_args
from isort.wrap_modes import WrapModes


def test_parse_args_deprecated_single_dash():
    # Test deprecated single dash args remapping (lines 931-933)
    # DEPRECATED_SINGLE_DASH_ARGS includes things like '-ac' (without leading dash in the set definition or with? Let's check: actually the set items start with '-' or not?)
    # Let's check DEPRECATED_SINGLE_DASH_ARGS elements.
    from isort.main import DEPRECATED_SINGLE_DASH_ARGS
    # Pick one element from DEPRECATED_SINGLE_DASH_ARGS, e.g., 'ac' or '-ac' depending on how it's defined.
    arg = next(iter(DEPRECATED_SINGLE_DASH_ARGS))
    # If the set contains strings like 'ac' or '-ac', let's test both or inspect.
    # Actually, let's pass `[arg]` where arg is in DEPRECATED_SINGLE_DASH_ARGS.
    res = parse_args([arg])
    assert "remapped_deprecated_args" in res


def test_parse_args_dont_order_by_type():
    res = parse_args(["--dont-order-by-type"])
    assert res["order_by_type"] is False
    assert "dont_order_by_type" not in res


def test_parse_args_dont_follow_links():
    res = parse_args(["--dont-follow-links"])
    assert res["follow_links"] is False
    assert "dont_follow_links" not in res


def test_parse_args_dont_float_to_top_false():
    res = parse_args(["--dont-float-to-top"])
    assert res["float_to_top"] is False
    assert "dont_float_to_top" not in res


def test_parse_args_float_to_top_conflict():
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--float-to-top", "--dont-float-to-top"])
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(exc_info.value)


def test_parse_args_multi_line_output_digit():
    res = parse_args(["--multi-line", "3"])
    assert res["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT


def test_parse_args_multi_line_output_name():
    res = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT"])
    assert res["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT
