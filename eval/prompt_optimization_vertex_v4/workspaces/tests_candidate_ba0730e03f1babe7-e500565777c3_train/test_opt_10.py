# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
import sys
from isort.main import parse_args, DEPRECATED_SINGLE_DASH_ARGS
from isort.wrap_modes import WrapModes


def test_parse_args_basic():
    # Test default argv=None and basic parsing
    args = parse_args([])
    assert isinstance(args, dict)


def test_parse_args_deprecated_single_dash():
    # Pick one deprecated single dash arg from DEPRECATED_SINGLE_DASH_ARGS
    dep_arg = next(iter(DEPRECATED_SINGLE_DASH_ARGS))
    args = parse_args([dep_arg])
    assert "remapped_deprecated_args" in args
    assert dep_arg in args["remapped_deprecated_args"]


def test_parse_args_dont_order_by_type():
    args = parse_args(["--dont-order-by-type"])
    assert args.get("order_by_type") is False
    assert "dont_order_by_type" not in args


def test_parse_args_dont_follow_links():
    args = parse_args(["--dont-follow-links"])
    assert args.get("follow_links") is False
    assert "dont_follow_links" not in args


def test_parse_args_dont_float_to_top_else():
    # Tests the else branch: arguments.get("float_to_top", False) is False
    args = parse_args(["--dont-float-to-top"])
    assert args.get("float_to_top") is False
    assert "dont_float_to_top" not in args


def test_parse_args_dont_float_to_top_conflict():
    # Tests the if branch raising sys.exit when both are set
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--float-to-top", "--dont-float-to-top"])
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(exc_info.value)


def test_parse_args_multi_line_output_digit():
    # Tests multi_line_output as digit string
    args = parse_args(["--multi-line", "3"])
    assert args.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT


def test_parse_args_multi_line_output_name():
    # Tests multi_line_output as non-digit string (enum name)
    args = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT"])
    assert args.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT
