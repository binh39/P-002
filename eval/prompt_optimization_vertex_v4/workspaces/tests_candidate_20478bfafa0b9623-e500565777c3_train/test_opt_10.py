# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import sys
import pytest
from isort.main import parse_args
from isort.wrap_modes import WrapModes


def test_parse_args_deprecated_and_flags():
    # Covers lines 928-935 (deprecated single dash args remapping)
    # Covers lines 938-939 (remapped_deprecated_args present)
    # Covers lines 940-942 (dont_order_by_type -> order_by_type = False)
    # Covers lines 943-945 (dont_follow_links -> follow_links = False)
    args = ["-df", "--dont-order-by-type", "--dont-follow-links"]
    parsed = parse_args(args)
    assert parsed["remapped_deprecated_args"] == ["-df"]
    assert parsed["show_diff"] is True
    assert parsed["order_by_type"] is False
    assert "dont_order_by_type" not in parsed
    assert parsed["follow_links"] is False
    assert "dont_follow_links" not in parsed


def test_parse_args_dont_float_to_top_conflict():
    # Covers lines 946-949 (dont_float_to_top when float_to_top is True -> sys.exit)
    args = ["--float-to-top", "--dont-float-to-top"]
    with pytest.raises(SystemExit) as exc_info:
        parse_args(args)
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(exc_info.value)


def test_parse_args_dont_float_to_top_false():
    # Covers lines 946-947, 950-951 (dont_float_to_top when float_to_top is not set -> float_to_top = False)
    args = ["--dont-float-to-top"]
    parsed = parse_args(args)
    assert parsed["float_to_top"] is False
    assert "dont_float_to_top" not in parsed


def test_parse_args_multi_line_output_digit():
    # Covers lines 952-955 (multi_line_output with digits converted to WrapModes(int))
    args = ["--multi-line", "1"]
    parsed = parse_args(args)
    assert parsed["multi_line_output"] == WrapModes.VERTICAL


def test_parse_args_multi_line_output_name():
    # Covers lines 952-953, 956-957 (multi_line_output with non-digit string converted via WrapModes[name])
    args = ["--multi-line", "VERTICAL"]
    parsed = parse_args(args)
    assert parsed["multi_line_output"] == WrapModes.VERTICAL
