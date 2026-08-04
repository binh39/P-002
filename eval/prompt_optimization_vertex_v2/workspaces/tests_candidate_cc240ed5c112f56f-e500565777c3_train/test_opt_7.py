# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args
from isort.wrap_modes import WrapModes


def test_parse_args_deprecated_args():
    # Covers lines 931-934 (remapped deprecated single dash args) and line 939
    res = parse_args(["-ac"])
    assert "-ac" in res["remapped_deprecated_args"]
    assert res["atomic"] is True


def test_parse_args_dont_order_by_type():
    # Covers lines 940-942
    res = parse_args(["--dont-order-by-type"])
    assert res["order_by_type"] is False
    assert "dont_order_by_type" not in res


def test_parse_args_dont_follow_links():
    # Covers lines 943-945
    res = parse_args(["--dont-follow-links"])
    assert res["follow_links"] is False
    assert "dont_follow_links" not in res


def test_parse_args_dont_float_to_top_exit():
    # Covers lines 947-949 (sys.exit when both --float-to-top and --dont-float-to-top are set)
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["--float-to-top", "--dont-float-to-top"])
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(excinfo.value)


def test_parse_args_dont_float_to_top_set_false():
    # Covers lines 947, 948, 950-951 (setting float_to_top to False when only --dont-float-to-top is provided)
    res = parse_args(["--dont-float-to-top"])
    assert res["float_to_top"] is False
    assert "dont_float_to_top" not in res


def test_parse_args_multi_line_output_digit():
    # Covers lines 953-955 (multi_line_output as digit string)
    res = parse_args(["--multi-line", "2"])
    assert res["multi_line_output"] == WrapModes.HANGING_INDENT


def test_parse_args_multi_line_output_non_digit():
    # Covers lines 953, 956-957 (multi_line_output as name string like HANGING_INDENT)
    res = parse_args(["--multi-line", "HANGING_INDENT"])
    assert res["multi_line_output"] == WrapModes.HANGING_INDENT
