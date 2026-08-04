# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args, DEPRECATED_SINGLE_DASH_ARGS
from isort.wrap_modes import WrapModes

def test_parse_args_deprecated_single_dash():
    # Covers lines 931-934 and 938-939
    arg = list(DEPRECATED_SINGLE_DASH_ARGS)[0]
    res = parse_args([arg])
    assert "remapped_deprecated_args" in res
    assert arg in res["remapped_deprecated_args"]

def test_parse_args_dont_order_by_type():
    # Covers lines 940-942
    res = parse_args(["--dont-order-by-type"])
    assert res.get("order_by_type") is False
    assert "dont_order_by_type" not in res

def test_parse_args_dont_follow_links():
    # Covers lines 943-945
    res = parse_args(["--dont-follow-links"])
    assert res.get("follow_links") is False
    assert "dont_follow_links" not in res

def test_parse_args_dont_float_to_top_else():
    # Covers lines 946-947, 949 (false branch), 951
    res = parse_args(["--dont-float-to-top"])
    assert res.get("float_to_top") is False
    assert "dont_float_to_top" not in res

def test_parse_args_dont_float_to_top_exit():
    # Covers lines 946-948 (true branch -> sys.exit)
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--float-to-top", "--dont-float-to-top"])
    assert "Can't set both" in str(exc_info.value)

def test_parse_args_multi_line_output_isdigit():
    # Covers lines 952-955
    res = parse_args(["--multi-line", "1"])
    assert res.get("multi_line_output") == WrapModes(1)

def test_parse_args_multi_line_output_name():
    # Covers lines 952-953, 956-957
    mode_name = list(WrapModes.__members__.keys())[0]
    res = parse_args(["--multi-line", mode_name])
    assert res.get("multi_line_output") == WrapModes[mode_name]
