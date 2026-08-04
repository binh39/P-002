# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import sys
import pytest
from isort.main import parse_args, DEPRECATED_SINGLE_DASH_ARGS
from isort.wrap_modes import WrapModes


def test_parse_args_default_and_empty():
    # Test with argv=None (uses sys.argv) and empty argv list
    old_argv = sys.argv
    try:
        sys.argv = ["isort"]
        args = parse_args(None)
        assert isinstance(args, dict)
    finally:
        sys.argv = old_argv

    args_empty = parse_args([])
    assert isinstance(args_empty, dict)


def test_parse_args_deprecated_single_dash():
    # Find one deprecated single dash arg from DEPRECATED_SINGLE_DASH_ARGS
    # Note: DEPRECATED_SINGLE_DASH_ARGS contains items like '-ac', but wait,
    # let's check how DEPRECATED_SINGLE_DASH_ARGS is populated and checked.
    # The check is: `if arg in DEPRECATED_SINGLE_DASH_ARGS:`
    dep_arg = next(iter(DEPRECATED_SINGLE_DASH_ARGS))
    args = parse_args([dep_arg, "--version"])
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


def test_parse_args_dont_float_to_top_false_case():
    # --dont-float-to-top without --float-to-top sets float_to_top to False
    args = parse_args(["--dont-float-to-top"])
    assert args.get("float_to_top") is False
    assert "dont_float_to_top" not in args


def test_parse_args_dont_float_to_top_conflict_exit():
    # Setting both --float-to-top and --dont-float-to-top calls sys.exit
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["--float-to-top", "--dont-float-to-top"])
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(excinfo.value)


def test_parse_args_multi_line_output_digit():
    # multi_line_output as a digit string (e.g., '3')
    args = parse_args(["--multi-line", "3"])
    assert args.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT


def test_parse_args_multi_line_output_name():
    # multi_line_output as a name string (e.g., 'VERTICAL_HANGING_INDENT')
    args = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT"])
    assert args.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT
