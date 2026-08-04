# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args, DEPRECATED_SINGLE_DASH_ARGS
from isort.wrap_modes import WrapModes

def test_parse_args_coverage():
    dep_arg = list(DEPRECATED_SINGLE_DASH_ARGS)[0]
    
    # Test multi_line_output with digit matching the exact value of VERTICAL_HANGING_INDENT (3)
    res1 = parse_args(["--multi-line", "3"])
    assert res1["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT

    # Test multi_line_output with string name
    wrap_mode_name = list(WrapModes.__members__.keys())[0]
    res2 = parse_args(["--multi-line", wrap_mode_name])
    assert res2["multi_line_output"] == WrapModes[wrap_mode_name]

    # Test dont_order_by_type
    res3 = parse_args(["--dont-order-by-type"])
    assert res3["order_by_type"] is False
    assert "dont_order_by_type" not in res3

    # Test dont_follow_links
    res4 = parse_args(["--dont-follow-links"])
    assert res4["follow_links"] is False
    assert "dont_follow_links" not in res4

    # Test dont_float_to_top setting float_to_top to False
    res5 = parse_args(["--dont-float-to-top"])
    assert res5["float_to_top"] is False
    assert "dont_float_to_top" not in res5

    # Test conflicting float_to_top and dont_float_to_top (raises SystemExit)
    with pytest.raises(SystemExit):
        parse_args(["--float-to-top", "--dont-float-to-top"])

    # Test deprecated single dash argument remapping (needs the leading dash, e.g. "-wl")
    res6 = parse_args([dep_arg])
    assert "remapped_deprecated_args" in res6
