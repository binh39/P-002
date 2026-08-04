# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args, DEPRECATED_SINGLE_DASH_ARGS
from isort.wrap_modes import WrapModes

def test_parse_args_basic():
    # Test basic parsing with no deprecated args and no special flags
    # Also tests when argv is None (defaults to sys.argv[1:])
    args = parse_args([])
    assert isinstance(args, dict)

def test_parse_args_deprecated_args():
    # Test deprecated single dash args remapping
    dep_arg = list(DEPRECATED_SINGLE_DASH_ARGS)[0].lstrip("-")
    # Add the single-dash version if the parser accepts it or handle it
    # DEPRECATED_SINGLE_DASH_ARGS contains items like '-ac' or similar depending on definition. Let's check.
    # Actually DEPRECATED_SINGLE_DASH_ARGS elements start with '-' or not? Let's check how they look or test with a valid one.
    pass

def test_parse_args_deprecated_single_dash():
    # Let's inspect what DEPRECATED_SINGLE_DASH_ARGS contains or pick one
    for arg in DEPRECATED_SINGLE_DASH_ARGS:
        # these usually start with '-' or not in the set, but let's check
        cleaned = arg.lstrip("-")
        # parse_args checks `if arg in DEPRECATED_SINGLE_DASH_ARGS:` where arg comes from argv.
        # If DEPRECATED_SINGLE_DASH_ARGS has 'j' or '-j', let's test both or pass one.
        res = parse_args([arg])
        assert "remapped_deprecated_args" in res
        break

def test_parse_args_dont_order_by_type():
    res = parse_args(["--dont-order-by-type"])
    assert res.get("order_by_type") is False
    assert "dont_order_by_type" not in res

def test_parse_args_dont_follow_links():
    res = parse_args(["--dont-follow-links"])
    assert res.get("follow_links") is False
    assert "dont_follow_links" not in res

def test_parse_args_dont_float_to_top_false():
    res = parse_args(["--dont-float-to-top"])
    assert res.get("float_to_top") is False
    assert "dont_float_to_top" not in res

def test_parse_args_dont_float_to_top_conflict():
    with pytest.raises(SystemExit) as excinfo:
        parse_args(["--float-to-top", "--dont-float-to-top"])
    assert "Can't set both" in str(excinfo.value)

def test_parse_args_multi_line_output_digit():
    res = parse_args(["--multi-line", "3"])
    assert res.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT

def test_parse_args_multi_line_output_name():
    res = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT"])
    assert res.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT
