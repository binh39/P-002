# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args
from isort.wrap_modes import WrapModes


def tests_parse_args_coverage():
    # 1. Test deprecated single dash args (lines 931-933, 938-939)
    # Using one from DEPRECATED_SINGLE_DASH_ARGS, e.g., 'ot' (which maps to order_by_type or similar)
    # Wait, the check in the code: `if arg in DEPRECATED_SINGLE_DASH_ARGS:` where elements in DEPRECATED_SINGLE_DASH_ARGS have '-' prefix or not?
    # Let's inspect DEPRECATED_SINGLE_DASH_ARGS items. They start with '-'!
    # Let's check what DEPRECATED_SINGLE_DASH_ARGS actually contains.
    from isort.main import DEPRECATED_SINGLE_DASH_ARGS
    deprecated_arg = next(iter(DEPRECATED_SINGLE_DASH_ARGS))

    res = parse_args([deprecated_arg, "."])
    assert "remapped_deprecated_args" in res
    assert deprecated_arg in res["remapped_deprecated_args"]

    # 2. Test dont_order_by_type (lines 940-942)
    res = parse_args(["--dont-order-by-type", "."])
    assert res.get("order_by_type") is False
    assert "dont_order_by_type" not in res

    # 3. Test dont_follow_links (lines 943-945)
    res = parse_args(["--dont-follow-links", "."])
    assert res.get("follow_links") is False
    assert "dont_follow_links" not in res

    # 4. Test dont_float_to_top without float_to_top (lines 946-947, 950-951)
    res = parse_args(["--dont-float-to-top", "."])
    assert res.get("float_to_top") is False
    assert "dont_float_to_top" not in res

    # 5. Test dont_float_to_top WITH float_to_top raising system exit (lines 946-949)
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["--float-to-top", "--dont-float-to-top", "."])
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(excinfo.value)

    # 6. Test multi_line_output with digit string (lines 953-955)
    res = parse_args(["--multi-line", "3", "."])
    assert res["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT

    # 7. Test multi_line_output with non-digit string (lines 956-957)
    res = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT", "."])
    assert res["multi_line_output"] == WrapModes.VERTICAL_HANGING_INDENT
