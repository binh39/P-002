# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args
from isort.wrap_modes import WrapModes


def test_parse_args_deprecated_and_flags():
    # Test DEPRECATED_SINGLE_DASH_ARGS remapping (e.g., if one of the deprecated single dash args is present)
    # Also test dont_order_by_type, dont_follow_links, dont_float_to_top (with float_to_top not set)
    # Let's find an item from DEPRECATED_SINGLE_DASH_ARGS without the leading '-'
    # The code checks `if arg in DEPRECATED_SINGLE_DASH_ARGS: remapped_deprecated_args.append(arg); argv[index] = f"-{arg}"`
    # Wait, DEPRECATED_SINGLE_DASH_ARGS contains strings starting with '-' like '-v' or similar, let's check what's actually in DEPRECATED_SINGLE_DASH_ARGS.
    from isort.main import DEPRECATED_SINGLE_DASH_ARGS
    if DEPRECATED_SINGLE_DASH_ARGS:
        sample_dep = list(DEPRECATED_SINGLE_DASH_ARGS)[0]
    else:
        sample_dep = "-v"

    # Test parse_args with deprecated arg, --dont-order-by-type, --dont-follow-links, --dont-float-to-top
    args = [sample_dep, "--dont-order-by-type", "--dont-follow-links", "--dont-float-to-top"]
    parsed = parse_args(args)
    assert "remapped_deprecated_args" in parsed
    assert parsed["order_by_type"] is False
    assert parsed["follow_links"] is False
    assert parsed["float_to_top"] is False


def test_parse_args_conflict_float_to_top():
    # Test --float-to-top and --dont-float-to-top together triggering sys.exit
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["--float-to-top", "--dont-float-to-top"])
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(excinfo.value)


def test_parse_args_multi_line_output_digit():
    # Test multi_line_output as a digit string
    parsed = parse_args(["--multi-line", "3"])
    assert isinstance(parsed["multi_line_output"], WrapModes)


def test_parse_args_multi_line_output_name():
    # Test multi_line_output as a non-digit string (e.g. VERTICAL)
    parsed = parse_args(["--multi-line", "VERTICAL"])
    assert isinstance(parsed["multi_line_output"], WrapModes)
