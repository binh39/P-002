# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
import sys
from isort.main import parse_args
from isort.wrap_modes import WrapModes


def test_parse_args_basic():
    # Test line 928-929 with argv=None and custom argv
    args = parse_args([])
    assert isinstance(args, dict)

    # Test deprecated single dash args (lines 931-934, 938-939)
    # Looking at DEPRECATED_SINGLE_DASH_ARGS, e.g., 'ac' without leading dash or with single dash?
    # Wait, the code checks: `if arg in DEPRECATED_SINGLE_DASH_ARGS:`
    # Let's check what DEPRECATED_SINGLE_DASH_ARGS contains: {'-ac', ...} or without dash?
    # Let's inspect DEPRECATED_SINGLE_DASH_ARGS or pass one from it.
    from isort.main import DEPRECATED_SINGLE_DASH_ARGS
    if DEPRECATED_SINGLE_DASH_ARGS:
        sample_dep = list(DEPRECATED_SINGLE_DASH_ARGS)[0]
        # sample_dep usually starts with '-' like '-ac' or 'ac'? Let's test with sample_dep directly
        parsed = parse_args([sample_dep, "some_file.py"])
        assert "remapped_deprecated_args" in parsed


def test_parse_args_dont_order_by_type():
    # Tests lines 940-942
    parsed = parse_args(["--dont-order-by-type", "some_file.py"])
    assert parsed.get("order_by_type") is False
    assert "dont_order_by_type" not in parsed


def test_parse_args_dont_follow_links():
    # Tests lines 943-945
    parsed = parse_args(["--dont-follow-links", "some_file.py"])
    assert parsed.get("follow_links") is False
    assert "dont_follow_links" not in parsed


def test_parse_args_dont_float_to_top_else():
    # Tests lines 946-951 (else branch where float_to_top is not set)
    parsed = parse_args(["--dont-float-to-top", "some_file.py"])
    assert parsed.get("float_to_top") is False
    assert "dont_float_to_top" not in parsed


def test_parse_args_dont_float_to_top_exit():
    # Tests lines 946-949 (sys.exit when both --float-to-top and --dont-float-to-top are set)
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--float-to-top", "--dont-float-to-top", "some_file.py"])
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(exc_info.value)


def test_parse_args_multi_line_output_digit():
    # Tests lines 952-955 (multi_line_output is digit)
    parsed = parse_args(["--multi-line", "3", "some_file.py"])
    assert parsed.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT


def test_parse_args_multi_line_output_name():
    # Tests lines 956-957 (multi_line_output is non-digit string, e.g. enum name)
    parsed = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT", "some_file.py"])
    assert parsed.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT
