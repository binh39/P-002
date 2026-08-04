# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
import sys
from isort.main import parse_args, DEPRECATED_SINGLE_DASH_ARGS
from isort.wrap_modes import WrapModes


def test_parse_args_basic_and_default():
    # Test default argv (None)
    old_argv = sys.argv
    try:
        sys.argv = ["isort"]
        args = parse_args(None)
        assert isinstance(args, dict)
    finally:
        sys.argv = old_argv


def test_parse_args_deprecated_args():
    # Find one deprecated single dash arg if available, or mock one
    deprecated_arg = next(iter(DEPRECATED_SINGLE_DASH_ARGS))
    # If the arg in DEPRECATED_SINGLE_DASH_ARGS has a leading dash like '-ac', 
    # the code checks `if arg in DEPRECATED_SINGLE_DASH_ARGS:` where `arg` comes from `argv`.
    # Usually argv items might be like 'ac' or '-ac'. Let's check how DEPRECATED_SINGLE_DASH_ARGS are defined.
    # Let's test with whatever is in DEPRECATED_SINGLE_DASH_ARGS.
    args = parse_args([deprecated_arg])
    assert "remapped_deprecated_args" in args


def test_parse_args_dont_order_by_type():
    args = parse_args(["--dont-order-by-type"])
    assert args.get("order_by_type") is False
    assert "dont_order_by_type" not in args


def test_parse_args_dont_follow_links():
    args = parse_args(["--dont-follow-links"])
    assert args.get("follow_links") is False
    assert "dont_follow_links" not in args


def test_parse_args_dont_float_to_top_else():
    args = parse_args(["--dont-float-to-top"])
    assert args.get("float_to_top") is False
    assert "dont_float_to_top" not in args


def test_parse_args_dont_float_to_top_conflict():
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--float-to-top", "--dont-float-to-top"])
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(exc_info.value)


def test_parse_args_multi_line_output_digit():
    # multi_line_output as digit string (e.g. "3")
    args = parse_args(["--multi-line", "3"])
    assert args["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT


def test_parse_args_multi_line_output_string():
    # multi_line_output as name string (e.g. "VERTICAL_HANGING_INDENT")
    args = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT"])
    assert args["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT
