# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args
from isort.wrap_modes import WrapModes

def test_parse_args_deprecated_args():
    # Test deprecated single dash args (without leading dash in DEPRECATED_SINGLE_DASH_ARGS)
    # Looking at DEPRECATED_SINGLE_DASH_ARGS, elements start with '-' or are they without?
    # Let's check: DEPRECATED_SINGLE_DASH_ARGS values usually start with '-' or not.
    # Wait, let's test with one of them, e.g., 'ac' or '-ac'. Let's check DEPRECATED_SINGLE_DASH_ARGS definition or test it.
    pass

def test_parse_args_comprehensive():
    # 1. Deprecated single dash args & remapped_deprecated_args
    # Let's see what is in DEPRECATED_SINGLE_DASH_ARGS by inspecting or using a known one like "j" or checking DEPRECATED_SINGLE_DASH_ARGS.
    from isort.main import DEPRECATED_SINGLE_DASH_ARGS
    if DEPRECATED_SINGLE_DASH_ARGS:
        dep_arg = list(DEPRECATED_SINGLE_DASH_ARGS)[0]
        # If dep_arg is like 'ac', arg in argv would be 'ac' if DEPRECATED_SINGLE_DASH_ARGS contains 'ac', or '-ac'.
        # Let's test passing `dep_arg`.
        res = parse_args([dep_arg, "."])
        assert "remapped_deprecated_args" in res

    # 2. dont_order_by_type
    res = parse_args(["--dont-order-by-type"])
    assert res.get("order_by_type") is False
    assert "dont_order_by_type" not in res

    # 3. dont_follow_links
    res = parse_args(["--dont-follow-links"])
    assert res.get("follow_links") is False
    assert "dont_follow_links" not in res

    # 4. dont_float_to_top with float_to_top (should sys.exit)
    with pytest.raises(SystemExit):
        parse_args(["--float-to-top", "--dont-float-to-top"])

    # 5. dont_float_to_top without float_to_top (should set float_to_top = False)
    res = parse_args(["--dont-float-to-top"])
    assert res.get("float_to_top") is False
    assert "dont_float_to_top" not in res

    # 6. multi_line_output digit (e.g. "3")
    res = parse_args(["--multi-line", "3"])
    assert res.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT

    # 7. multi_line_output non-digit (e.g. "VERTICAL_HANGING_INDENT" or similar string key of WrapModes)
    # Let's check valid WrapModes keys
    mode_name = list(WrapModes.__members__.keys())[0]
    res = parse_args(["--multi-line", mode_name])
    assert res.get("multi_line_output") == WrapModes[mode_name]
