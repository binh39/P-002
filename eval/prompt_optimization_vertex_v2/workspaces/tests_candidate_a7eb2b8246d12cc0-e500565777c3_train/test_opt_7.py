# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args
from isort.wrap_modes import WrapModes


def test_parse_args_deprecated_args():
    # Test DEPRECATED_SINGLE_DASH_ARGS remapping (e.g., 'ac' or similar if in DEPRECATED_SINGLE_DASH_ARGS)
    # Let's check one that starts with '-' or without depending on how DEPRECATED_SINGLE_DASH_ARGS defines them.
    # Looking at DEPRECATED_SINGLE_DASH_ARGS, elements start with '-' like '-ac'.
    # Wait, argv items in DEPRECATED_SINGLE_DASH_ARGS check: arg in DEPRECATED_SINGLE_DASH_ARGS.
    # Let's inspect DEPRECATED_SINGLE_DASH_ARGS or pass one of them.
    from isort.main import DEPRECATED_SINGLE_DASH_ARGS
    if DEPRECATED_SINGLE_DASH_ARGS:
        dep_arg = list(DEPRECATED_SINGLE_DASH_ARGS)[0]
        # remove leading dash if check expects without dash or with dash?
        # line 932: if arg in DEPRECATED_SINGLE_DASH_ARGS:
        # line 934: argv[index] = f"-{arg}"
        # This means arg does NOT have the extra dash in DEPRECATED_SINGLE_DASH_ARGS, or does it?
        # Let's test with the exact string in DEPRECATED_SINGLE_DASH_ARGS.
        res = parse_args([dep_arg])
        assert "remapped_deprecated_args" in res


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
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["--float-to-top", "--dont-float-to-top"])
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(excinfo.value)


def test_parse_args_multi_line_output_digit():
    res = parse_args(["--multi-line", "3"])
    assert res.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT


def test_parse_args_multi_line_output_name():
    res = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT"])
    assert res.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT
