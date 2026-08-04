# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args
from isort.wrap_modes import WrapModes


def test_parse_args_deprecated_and_flags():
    # Test deprecated single dash args requiring an argument (like "-sp some_path")
    # Plus dont_order_by_type, dont_follow_links, dont_float_to_top (set to False when float_to_top is not True)
    args = ["-sp", "some_path", "--dont-order-by-type", "--dont-follow-links", "--dont-float-to-top"]
    parsed = parse_args(args)
    assert parsed.get("remapped_deprecated_args") == ["-sp"]
    assert parsed.get("order_by_type") is False
    assert "dont_order_by_type" not in parsed
    assert parsed.get("follow_links") is False
    assert "dont_follow_links" not in parsed
    assert parsed.get("float_to_top") is False
    assert "dont_float_to_top" not in parsed


def test_parse_args_conflict_float_to_top():
    # Test --dont-float-to-top and --float-to-top conflict (lines 948-949)
    args = ["--float-to-top", "--dont-float-to-top"]
    with pytest.raises(SystemExit) as exc_info:
        parse_args(args)
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(exc_info.value)


def test_parse_args_multi_line_output_digit():
    # Test multi_line_output as digit (lines 953-955)
    args = ["--multi-line", "3"]
    parsed = parse_args(args)
    assert parsed.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT


def test_parse_args_multi_line_output_name():
    # Test multi_line_output as string name (lines 956-957)
    args = ["--multi-line", "VERTICAL_HANGING_INDENT"]
    parsed = parse_args(args)
    assert parsed.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT
