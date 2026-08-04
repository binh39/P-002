# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
import sys
from isort.main import parse_args
from isort.wrap_modes import WrapModes

def test_parse_args_deprecated_and_dont_flags():
    # Test deprecated single dash args (lines 931-934) and dont_order_by_type / dont_follow_links (lines 940-945)
    args = ["-df", "--dont-order-by-type", "--dont-follow-links"]
    parsed = parse_args(args)
    assert parsed["remapped_deprecated_args"] == ["-df"]
    assert parsed["order_by_type"] is False
    assert "dont_order_by_type" not in parsed
    assert parsed["follow_links"] is False
    assert "dont_follow_links" not in parsed

def test_parse_args_dont_float_to_top_exclusive():
    # Test dont_float_to_top when float_to_top is True (lines 946-949)
    args = ["--float-to-top", "--dont-float-to-top"]
    with pytest.raises(SystemExit) as excinfo:
        parse_args(args)
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(excinfo.value)

def test_parse_args_dont_float_to_top_false():
    # Test dont_float_to_top when float_to_top is not set (lines 946-951)
    args = ["--dont-float-to-top"]
    parsed = parse_args(args)
    assert parsed["float_to_top"] is False
    assert "dont_float_to_top" not in parsed

def test_parse_args_multi_line_output_digit():
    # Test multi_line_output with digit string (lines 952-955)
    args = ["--multi-line", "2"]
    parsed = parse_args(args)
    assert parsed["multi_line_output"] == WrapModes.HANGING_INDENT

def test_parse_args_multi_line_output_name():
    # Test multi_line_output with enum name string (lines 952-953, 956-957)
    args = ["--multi-line", "VERTICAL_HANGING_INDENT"]
    parsed = parse_args(args)
    assert parsed["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT
