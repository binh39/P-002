# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args, DEPRECATED_SINGLE_DASH_ARGS
from isort.wrap_modes import WrapModes

def test_parse_args_deprecated_and_flags():
    # Test deprecated single dash args (stripping leading dash or matching exact in set)
    # Looking at DEPRECATED_SINGLE_DASH_ARGS, they start with '-' (e.g. '-ac').
    # But wait, argv items are checked against DEPRECATED_SINGLE_DASH_ARGS.
    # Let's check an actual deprecated single dash arg from the set, e.g. next(iter(DEPRECATED_SINGLE_DASH_ARGS))
    dep_arg = next(iter(DEPRECATED_SINGLE_DASH_ARGS))
    # If dep_arg is e.g. '-ac', line 932 checks `if arg in DEPRECATED_SINGLE_DASH_ARGS:`
    # Wait, if `dep_arg` is in the set, it starts with '-' usually. Let's inspect DEPRECATED_SINGLE_DASH_ARGS content.
    # If the elements start with '-', then passing that exact string triggers remapped_deprecated_args.
    args = [dep_arg, "--dont-order-by-type", "--dont-follow-links"]
    res = parse_args(args)
    assert "remapped_deprecated_args" in res
    assert res["order_by_type"] is False
    assert res["follow_links"] is False

def test_parse_args_dont_float_to_top_else():
    # If dont_float_to_top is passed, but float_to_top is not True, it sets float_to_top to False
    res = parse_args(["--dont-float-to-top"])
    assert res["float_to_top"] is False
    assert "dont_float_to_top" not in res

def test_parse_args_float_to_top_conflict():
    # If both float_to_top and dont_float_to_top are passed, it should sys.exit
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--float-to-top", "--dont-float-to-top"])
    assert "Can't set both" in str(exc_info.value)

def test_parse_args_multi_line_output_digit():
    # multi_line_output as digit string
    res = parse_args(["--multi-line", "3"])
    assert isinstance(res["multi_line_output"], WrapModes)

def test_parse_args_multi_line_output_name():
    # multi_line_output as non-digit string (e.g. "VERTICAL_HANGING_INDENT" or similar WrapModes name)
    # Let's find a valid WrapModes key name
    mode_name = next(iter(WrapModes.__members__.keys()))
    res = parse_args(["--multi-line", mode_name])
    assert res["multi_line_output"] == WrapModes[mode_name]
