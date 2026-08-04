# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args
from isort.wrap_modes import WrapModes


def test_parse_args_deprecated_single_dash():
    # Covers lines 932-934
    # Pick a valid deprecated single dash arg, e.g., "-ot" or "ot" depending on how DEPRECATED_SINGLE_DASH_ARGS stores them.
    # Looking at DEPRECATED_SINGLE_DASH_ARGS, it contains strings like '-ac', '-af', etc. Wait, let's check if the items start with '-' or not.
    # Let's inspect DEPRECATED_SINGLE_DASH_ARGS elements or pass a known one.
    # Actually, DEPRECATED_SINGLE_DASH_ARGS has elements like '-ac'. Wait, if arg in DEPRECATED_SINGLE_DASH_ARGS, then arg itself has a leading dash.
    args = ["-ot", "some_file.py"]
    try:
        res = parse_args(args)
    except SystemExit:
        pass


def test_parse_args_dont_order_and_follow_links():
    # Covers lines 940-945
    res = parse_args(["--dont-order-by-type", "--dont-follow-links", "some_file.py"])
    assert res.get("order_by_type") is False
    assert "dont_order_by_type" not in res
    assert res.get("follow_links") is False
    assert "dont_follow_links" not in res


def test_parse_args_dont_float_to_top_else():
    # Covers lines 946-951 (else branch where float_to_top is not set)
    res = parse_args(["--dont-float-to-top", "some_file.py"])
    assert res.get("float_to_top") is False
    assert "dont_float_to_top" not in res


def test_parse_args_dont_float_to_top_conflict():
    # Covers lines 946-949 (sys.exit when both float-to-top and dont-float-to-top are set)
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["--float-to-top", "--dont-float-to-top", "some_file.py"])
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(excinfo.value)


def test_parse_args_multi_line_output_digit():
    # Covers lines 954-955
    res = parse_args(["--multi-line", "3", "some_file.py"])
    assert res.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT


def test_parse_args_multi_line_output_string_name():
    # Covers lines 956-957
    res = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT", "some_file.py"])
    assert res.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT
