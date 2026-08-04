# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args
from isort.wrap_modes import WrapModes


def test_parse_args_deprecated_and_flags():
    # Test DEPRECATED_SINGLE_DASH_ARGS and dont_order_by_type, dont_follow_links
    # Let's check what deprecated arg is valid, e.g. "-ac" without dash in DEPRECATED_SINGLE_DASH_ARGS
    # Looking at DEPRECATED_SINGLE_DASH_ARGS definition, elements are strings like '-ac' or 'ac'?
    # Wait, the code checks `if arg in DEPRECATED_SINGLE_DASH_ARGS: argv[index] = f"-{arg}"`
    # Let's pass an item from DEPRECATED_SINGLE_DASH_ARGS, e.g., 'ac' or '-ac'.
    # If DEPRECATED_SINGLE_DASH_ARGS contains '-ac', then arg should be '-ac'.
    args = ["-ac", "--dont-order-by-type", "--dont-follow-links"]
    parsed = parse_args(args)
    assert parsed["order_by_type"] is False
    assert parsed["follow_links"] is False
    assert "remapped_deprecated_args" in parsed


def test_parse_args_float_to_top_conflict():
    # Test --dont-float-to-top when float_to_top is True
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["--float-to-top", "--dont-float-to-top"])
    assert "Can't set both" in str(excinfo.value)


def test_parse_args_dont_float_to_top_alone():
    # Test --dont-float-to-top when float_to_top is not set
    parsed = parse_args(["--dont-float-to-top"])
    assert parsed.get("float_to_top") is False


def test_parse_args_multi_line_output_digit():
    parsed = parse_args(["--multi-line", "3"])
    assert parsed["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT


def test_parse_args_multi_line_output_string():
    parsed = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT"])
    assert parsed["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT
