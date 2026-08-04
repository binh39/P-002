# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
import sys
from isort.main import parse_args
from isort.wrap_modes import WrapModes

def test_parse_args_basic_and_defaults():
    # Test argv=None (uses sys.argv) and basic parsing
    args = parse_args([])
    assert isinstance(args, dict)

def test_parse_args_deprecated_single_dash():
    # Test deprecated single dash arguments remapping
    # Pick one from DEPRECATED_SINGLE_DASH_ARGS if possible, e.g. 'sp' or similar if present without leading dash or with single dash
    # DEPRECATED_SINGLE_DASH_ARGS contains items like '-ac', but wait, let's check what DEPRECATED_SINGLE_DASH_ARGS elements look like.
    # From get_info, DEPRECATED_SINGLE_DASH_ARGS has items starting with '-' like '-ac', '-af', etc.
    # Let's verify how `arg in DEPRECATED_SINGLE_DASH_ARGS` matches.
    from isort.main import DEPRECATED_SINGLE_DASH_ARGS
    dep_arg = list(DEPRECATED_SINGLE_DASH_ARGS)[0]  # e.g. '-ac'
    # If the item in DEPRECATED_SINGLE_DASH_ARGS starts with '-', passing it will trigger:
    # arg in DEPRECATED_SINGLE_DASH_ARGS -> remapped_deprecated_args.append(arg); argv[index] = f"-{arg}" -> becomes '--ac' or similar? Wait, f"-{arg}" prepends another '-'!
    # Let's test with a valid deprecated arg if any exist or just pass `dep_arg`.
    try:
        parse_args([dep_arg, "dummy.py"])
    except SystemExit:
        pass

def test_parse_args_dont_order_by_type():
    args = parse_args(["--dont-order-by-type"])
    assert args.get("order_by_type") is False
    assert "dont_order_by_type" not in args

def test_parse_args_dont_follow_links():
    args = parse_args(["--dont-follow-links"])
    assert args.get("follow_links") is False
    assert "dont_follow_links" not in args

def test_parse_args_dont_float_to_top_else():
    # dont_float_to_top without float_to_top set -> sets float_to_top = False
    args = parse_args(["--dont-float-to-top"])
    assert args.get("float_to_top") is False
    assert "dont_float_to_top" not in args

def test_parse_args_dont_float_to_top_conflict():
    # both float_to_top and dont_float_to_top -> sys.exit
    with pytest.raises(SystemExit):
        parse_args(["--float-to-top", "--dont-float-to-top"])

def test_parse_args_multi_line_output_digit():
    args = parse_args(["--multi-line", "3"])
    assert args["multi_line_output"] == WrapModes(3)

def test_parse_args_multi_line_output_str():
    args = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT"])
    assert args["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT
