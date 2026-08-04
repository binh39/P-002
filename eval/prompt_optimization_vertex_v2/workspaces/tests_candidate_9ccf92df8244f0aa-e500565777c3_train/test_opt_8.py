# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 957]]}

import pytest
from isort.main import parse_args, DEPRECATED_SINGLE_DASH_ARGS
from isort.wrap_modes import WrapModes


def test_parse_args_deprecated_and_flags():
    # Pick a deprecated arg that doesn't expect an argument value, e.g., '-ac' or '-df' if available, 
    # or just test with a safe one like '-ac' (add-imports/etc - let's check DEPRECATED_SINGLE_DASH_ARGS).
    # Since DEPRECATED_SINGLE_DASH_ARGS contains items without dash or with dash? 
    # The code does: if arg in DEPRECATED_SINGLE_DASH_ARGS: argv[index] = f"-{arg}"
    # This means elements in DEPRECATED_SINGLE_DASH_ARGS are like 'ac', 'df', etc. without leading dashes.
    # Let's find one that is a flag (does not require extra value) or use `-ac` if it's stored without dash.
    # Actually, let's use 'ac' if present in DEPRECATED_SINGLE_DASH_ARGS, or pick any element from it.
    dep_arg = next(iter(DEPRECATED_SINGLE_DASH_ARGS))

    args = [dep_arg, "--dont-order-by-type", "--dont-follow-links", "--dont-float-to-top"]
    parsed = parse_args(args)
    assert parsed["order_by_type"] is False
    assert parsed["follow_links"] is False
    assert parsed["float_to_top"] is False
    assert "remapped_deprecated_args" in parsed


def test_parse_args_float_to_top_conflict():
    args = ["--float-to-top", "--dont-float-to-top"]
    with pytest.raises(SystemExit) as excinfo:
        parse_args(args)
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(excinfo.value)


def test_parse_args_multi_line_output_enum_name():
    # isort uses `-m` for multi_line_output (not `--multi-line-output`)
    args = ["-m", "GRID"]
    parsed = parse_args(args)
    assert parsed["multi_line_output"] == WrapModes.GRID
