# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args
from isort.wrap_modes import WrapModes


def test_parse_args_deprecated_single_dash():
    # Tests deprecated single dash argument remapping (lines 931-933, 938-939)
    # Using one from DEPRECATED_SINGLE_DASH_ARGS, e.g. '-ac' (without leading dash in set? Wait, let's check DEPRECATED_SINGLE_DASH_ARGS items)
    # Let's check what DEPRECATED_SINGLE_DASH_ARGS contains: values in set start with '-' or not?
    # Let's inspect DEPRECATED_SINGLE_DASH_ARGS via parse_args test or checking elements.
    # Actually, let's check one or pass an invalid/arbitrary or valid deprecated arg if we know it.
    # Let's test with a mock or check DEPRECATED_SINGLE_DASH_ARGS first.
    from isort.main import DEPRECATED_SINGLE_DASH_ARGS
    deg_arg = list(DEPRECATED_SINGLE_DASH_ARGS)[0]
    # If elements in DEPRECATED_SINGLE_DASH_ARGS start with '-', then `arg in DEPRECATED_SINGLE_DASH_ARGS` matches.
    # Let's call parse_args with [deg_arg] or similar, or just test all branches explicitly.
    args = parse_args([deg_arg, "some_file.py"])
    assert "remapped_deprecated_args" in args


def test_parse_args_dont_order_by_type():
    args = parse_args(["--dont-order-by-type", "some_file.py"])
    assert args.get("order_by_type") is False
    assert "dont_order_by_type" not in args


def test_parse_args_dont_follow_links():
    args = parse_args(["--dont-follow-links", "some_file.py"])
    assert args.get("follow_links") is False
    assert "dont_follow_links" not in args


def test_parse_args_dont_float_to_top_conflict():
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["--float-to-top", "--dont-float-to-top", "some_file.py"])
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(excinfo.value)


def test_parse_args_dont_float_to_top_set_false():
    args = parse_args(["--dont-float-to-top", "some_file.py"])
    assert args.get("float_to_top") is False
    assert "dont_float_to_top" not in args


def test_parse_args_multi_line_output_digit():
    args = parse_args(["--multi-line", "3", "some_file.py"])
    assert args.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT


def test_parse_args_multi_line_output_string():
    args = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT", "some_file.py"])
    assert args.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT
