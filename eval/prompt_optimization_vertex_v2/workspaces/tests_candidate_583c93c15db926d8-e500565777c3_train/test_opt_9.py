# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args, DEPRECATED_SINGLE_DASH_ARGS
from isort.wrap_modes import WrapModes


def test_parse_args_deprecated_and_flags():
    # Test deprecated single dash args (without leading single dash in input as expected by DEPRECATED_SINGLE_DASH_ARGS check)
    # Let's pick one from DEPRECATED_SINGLE_DASH_ARGS, e.g. a valid one or whatever is checked.
    # Looking at DEPRECATED_SINGLE_DASH_ARGS items, they start with '-' in the set or not?
    # Wait, let's inspect DEPRECATED_SINGLE_DASH_ARGS elements.
    dep_arg = next(iter(DEPRECATED_SINGLE_DASH_ARGS))
    # If the set items include '-', then arg in DEPRECATED_SINGLE_DASH_ARGS expects the item to have '-'.
    # Let's pass `dep_arg` directly in argv.
    
    # Also test dont_order_by_type, dont_follow_links
    # Also test dont_float_to_top setting float_to_top to False (when float_to_top is not set)
    args = [dep_arg, "--dont-order-by-type", "--dont-follow-links", "--dont-float-to-top"]
    parsed = parse_args(args)
    
    assert "remapped_deprecated_args" in parsed
    assert parsed["order_by_type"] is False
    assert "dont_order_by_type" not in parsed
    assert parsed["follow_links"] is False
    assert "dont_follow_links" not in parsed
    assert parsed["float_to_top"] is False
    assert "dont_float_to_top" not in parsed


def test_parse_args_conflict_float_to_top():
    # Test line 948-949: both --float-to-top and --dont-float-to-top supplied
    args = ["--float-to-top", "--dont-float-to-top"]
    with pytest.raises(SystemExit) as excinfo:
        parse_args(args)
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(excinfo.value)


def test_parse_args_multi_line_output_digit():
    # Test line 954-955: multi_line_output is digit string
    args = ["--multi-line", "3"]
    parsed = parse_args(args)
    assert parsed["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT


def test_parse_args_multi_line_output_name():
    # Test line 957: multi_line_output is non-digit string (enum name)
    args = ["--multi-line", "VERTICAL_HANGING_INDENT"]
    parsed = parse_args(args)
    assert parsed["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT
