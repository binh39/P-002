# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
import sys
from isort.main import parse_args
from isort.wrap_modes import WrapModes

def test_parse_args_deprecated_args():
    # Covers lines 932-934: arg in DEPRECATED_SINGLE_DASH_ARGS
    # e.g., '-df' is in DEPRECATED_SINGLE_DASH_ARGS
    args = parse_args(["-df"])
    assert "-df" in args["remapped_deprecated_args"]
    assert args["show_diff"] is True

def test_parse_args_dont_order_by_type():
    # Covers lines 940-942: 'dont_order_by_type' in arguments
    args = parse_args(["--dont-order-by-type"])
    assert args["order_by_type"] is False
    assert "dont_order_by_type" not in args

def test_parse_args_dont_follow_links():
    # Covers lines 943-945: 'dont_follow_links' in arguments
    args = parse_args(["--dont-follow-links"])
    assert args["follow_links"] is False
    assert "dont_follow_links" not in args

def test_parse_args_dont_float_to_top_conflict():
    # Covers lines 946-949: sys.exit when both --float-to-top and --dont-float-to-top are passed
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["--float-to-top", "--dont-float-to-top"])
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(excinfo.value)

def test_parse_args_dont_float_to_top_no_conflict():
    # Covers lines 946-947 and 950-951: --dont-float-to-top without --float-to-top
    args = parse_args(["--dont-float-to-top"])
    assert args["float_to_top"] is False
    assert "dont_float_to_top" not in args

def test_parse_args_multi_line_output_digit():
    # Covers lines 954-955: multi_line_output.isdigit()
    args = parse_args(["--multi-line", "1"])
    assert args["multi_line_output"] == WrapModes.VERTICAL

def test_parse_args_multi_line_output_non_digit():
    # Covers lines 956-957: multi_line_output is non-digit (string key in WrapModes)
    args = parse_args(["--multi-line", "VERTICAL"])
    assert args["multi_line_output"] == WrapModes.VERTICAL
