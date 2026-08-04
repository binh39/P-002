# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args
from isort.wrap_modes import WrapModes


def test_parse_args_deprecated_single_dash():
    # Covers lines 931-934 (DEPRECATED_SINGLE_DASH_ARGS matching) and line 938-939
    # DEPRECATED_SINGLE_DASH_ARGS items have the leading '-' in the set or not?
    # Let's check DEPRECATED_SINGLE_DASH_ARGS values. They start with '-' in the definition?
    # Wait, the get_info for DEPRECATED_SINGLE_DASH_ARGS showed:
    # {'-ac', '-af', ...}
    # Let's pass one of them like '-ac' or 'ac'? Wait, arg in DEPRECATED_SINGLE_DASH_ARGS.
    # If the set contains '-ac', then arg should be '-ac'.
    args = parse_args(["-ac", "some_file.py"])
    assert "remapped_deprecated_args" in args
    assert "-ac" in args["remapped_deprecated_args"]


def test_parse_args_dont_order_by_type():
    # Covers lines 940-942
    args = parse_args(["--dont-order-by-type", "some_file.py"])
    assert args["order_by_type"] is False
    assert "dont_order_by_type" not in args


def test_parse_args_dont_follow_links():
    # Covers lines 943-945
    args = parse_args(["--dont-follow-links", "some_file.py"])
    assert args["follow_links"] is False
    assert "dont_follow_links" not in args


def test_parse_args_dont_float_to_top_false():
    # Covers lines 946-947 and line 951 (else branch when float_to_top is not True)
    args = parse_args(["--dont-float-to-top", "some_file.py"])
    assert args["float_to_top"] is False
    assert "dont_float_to_top" not in args


def test_parse_args_dont_float_to_top_conflict():
    # Covers lines 948-949 (sys.exit when both float-to-top and dont-float-to-top are set)
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--float-to-top", "--dont-float-to-top", "some_file.py"])
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(exc_info.value)


def test_parse_args_multi_line_output_digit():
    # Covers lines 952-955 (multi_line_output isdigit -> WrapModes(int(...)))
    args = parse_args(["--multi-line", "3", "some_file.py"])
    assert args["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT


def test_parse_args_multi_line_output_string():
    # Covers lines 952-953, 956-957 (multi_line_output not digit -> WrapModes[...])
    args = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT", "some_file.py"])
    assert args["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT
