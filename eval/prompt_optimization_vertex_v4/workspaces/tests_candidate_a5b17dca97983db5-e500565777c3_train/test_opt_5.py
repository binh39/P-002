# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args
from isort.wrap_modes import WrapModes

def test_parse_args_deprecated_args():
    # Test deprecated single dash args remapping
    # Pick one from DEPRECATED_SINGLE_DASH_ARGS, e.g. 'sp' if it's in there or check how DEPRECATED_SINGLE_DASH_ARGS are defined.
    # Note that DEPRECATED_SINGLE_DASH_ARGS typically include the leading dash or not? Let's check:
    # Actually DEPRECATED_SINGLE_DASH_ARGS has items like '-ac', etc. Wait, let's check what DEPRECATED_SINGLE_DASH_ARGS contains or pass a valid one.
    from isort.main import DEPRECATED_SINGLE_DASH_ARGS
    dep = list(DEPRECATED_SINGLE_DASH_ARGS)[0].lstrip("-")
    args = [f"-{dep}", "some_file.py"]
    res = parse_args(args)
    assert "remapped_deprecated_args" in res

def test_parse_args_dont_order_by_type():
    res = parse_args(["--dont-order-by-type", "some_file.py"])
    assert res.get("order_by_type") is False
    assert "dont_order_by_type" not in res

def test_parse_args_dont_follow_links():
    res = parse_args(["--dont-follow-links", "some_file.py"])
    assert res.get("follow_links") is False
    assert "dont_follow_links" not in res

def test_parse_args_dont_float_to_top_else():
    res = parse_args(["--dont-float-to-top", "some_file.py"])
    assert res.get("float_to_top") is False
    assert "dont_float_to_top" not in res

def test_parse_args_dont_float_to_top_exit():
    with pytest.raises(SystemExit):
        parse_args(["--float-to-top", "--dont-float-to-top", "some_file.py"])

def test_parse_args_multi_line_output_digit():
    res = parse_args(["--multi-line", "3", "some_file.py"])
    assert res.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT

def test_parse_args_multi_line_output_name():
    res = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT", "some_file.py"])
    assert res.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT
