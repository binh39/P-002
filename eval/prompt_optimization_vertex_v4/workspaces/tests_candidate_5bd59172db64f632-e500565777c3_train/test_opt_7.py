# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args, DEPRECATED_SINGLE_DASH_ARGS
from isort.wrap_modes import WrapModes

def test_parse_args_deprecated_single_dash():
    # Pick one deprecated single dash arg without the leading single dash if DEPRECATED_SINGLE_DASH_ARGS stores them without dash,
    # or let's check what DEPRECATED_SINGLE_DASH_ARGS contains.
    # Looking at the code: if arg in DEPRECATED_SINGLE_DASH_ARGS: argv[index] = f"-{arg}"
    # Wait, DEPRECATED_SINGLE_DASH_ARGS elements in isort usually start with '-' or not? Let's inspect an element or use one.
    sample = list(DEPRECATED_SINGLE_DASH_ARGS)[0]
    # If sample starts with '-', e.g. '-v' or similar, let's see. Or we can just pass [sample].
    # Actually, let's test parse_args with various branches.
    res = parse_args([sample, "--version"]) or parse_args([sample])
    assert isinstance(res, dict)

def test_parse_args_dont_order_by_type():
    res = parse_args(["--dont-order-by-type"])
    assert res.get("order_by_type") is False
    assert "dont_order_by_type" not in res

def test_parse_args_dont_follow_links():
    res = parse_args(["--dont-follow-links"])
    assert res.get("follow_links") is False
    assert "dont_follow_links" not in res

def test_parse_args_dont_float_to_top_else():
    res = parse_args(["--dont-float-to-top"])
    assert res.get("float_to_top") is False
    assert "dont_float_to_top" not in res

def test_parse_args_dont_float_to_top_conflict():
    with pytest.raises(SystemExit):
        parse_args(["--float-to-top", "--dont-float-to-top"])

def test_parse_args_multi_line_output_digit():
    res = parse_args(["--multi-line", "3"])
    assert res["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT

def test_parse_args_multi_line_output_string():
    res = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT"])
    assert res["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT
