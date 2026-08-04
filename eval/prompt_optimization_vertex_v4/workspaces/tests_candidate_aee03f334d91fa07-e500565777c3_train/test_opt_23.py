# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 936, 937, 938, 940, 943, 946, 947, 948, 949, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [938, 940], [940, 943], [943, 946], [946, 947], [946, 952], [948, 949], [953, 954], [954, 955], [954, 957]]}

import sys
import pytest
from isort.main import parse_args, DEPRECATED_SINGLE_DASH_ARGS
from isort.wrap_modes import WrapModes


def test_parse_args_conflict_float_to_top():
    # Test conflict between float-to-top and dont-float-to-top
    args = ["--float-to-top", "--dont-float-to-top"]
    with pytest.raises(SystemExit) as excinfo:
        parse_args(args)
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(excinfo.value)

def test_parse_args_multi_line_output_digit():
    # Test multi_line_output as digit string
    args = ["--multi-line", "3"]
    parsed = parse_args(args)
    assert parsed["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT

def test_parse_args_multi_line_output_name():
    # Test multi_line_output as non-digit string (e.g. enum name)
    args = ["--multi-line", "VERTICAL_HANGING_INDENT"]
    parsed = parse_args(args)
    assert parsed["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT

def test_parse_args_default_argv():
    # Test with argv=None (uses sys.argv)
    old_sys_argv = sys.argv
    try:
        sys.argv = ["isort", "--help"]
        with pytest.raises(SystemExit):
            parse_args(None)
    finally:
        sys.argv = old_sys_argv
