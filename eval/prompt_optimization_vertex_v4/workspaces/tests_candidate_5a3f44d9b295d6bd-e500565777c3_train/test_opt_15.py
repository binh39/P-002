# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args
from isort.wrap_modes import WrapModes


def test_parse_args_deprecated_args():
    # Test DEPRECATED_SINGLE_DASH_ARGS remapping. 
    # For instance, 'sp' is a deprecated single dash arg (which expects a value like 'some_path').
    # When passed as '-sp', it gets remapped to '--sp' and an argument value is supplied.
    args = parse_args(["-sp", "some_path"])
    assert "remapped_deprecated_args" in args
    assert args.get("settings_path") == "some_path"


def test_parse_args_dont_order_by_type():
    args = parse_args(["--dont-order-by-type"])
    assert args.get("order_by_type") is False
    assert "dont_order_by_type" not in args


def test_parse_args_dont_follow_links():
    args = parse_args(["--dont-follow-links"])
    assert args.get("follow_links") is False
    assert "dont_follow_links" not in args


def test_parse_args_dont_float_to_top():
    # Case where float_to_top is not set
    args = parse_args(["--dont-float-to-top"])
    assert args.get("float_to_top") is False
    assert "dont_float_to_top" not in args

    # Case where float_to_top is also set (should sys.exit)
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--dont-float-to-top", "--float-to-top"])
    assert "Can't set both" in str(exc_info.value)


def test_parse_args_multi_line_output_digit():
    args = parse_args(["--multi-line", "3"])
    assert args.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT


def test_parse_args_multi_line_output_name():
    args = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT"])
    assert args.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT
