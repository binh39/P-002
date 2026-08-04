# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
import sys
from isort.main import parse_args, DEPRECATED_SINGLE_DASH_ARGS
from isort.wrap_modes import WrapModes


def test_parse_args_basic_and_defaults():
    args = parse_args([])
    assert isinstance(args, dict)


def test_parse_args_deprecated_single_dash():
    # Pick a deprecated single dash argument from DEPRECATED_SINGLE_DASH_ARGS,
    # e.g., '-ac' or '-df'. Note that DEPRECATED_SINGLE_DASH_ARGS contains strings
    # starting with '-' (like '-ac', '-df', etc.).
    dep_arg = next(iter(DEPRECATED_SINGLE_DASH_ARGS))
    # Remove leading '-' to simulate passing it without hyphen or keep it depending on how check works.
    # The check is `if arg in DEPRECATED_SINGLE_DASH_ARGS: remapped_deprecated_args.append(arg); argv[index] = f"-{arg}"`
    # So `arg` itself must be in DEPRECATED_SINGLE_DASH_ARGS.
    # If DEPRECATED_SINGLE_DASH_ARGS contains '-ac', then `arg` needs to be '-ac', but wait:
    # If `arg` is '-ac', then `f"-{arg}"` becomes `--ac` or `---ac`?
    # Let's inspect DEPRECATED_SINGLE_DASH_ARGS items carefully or just pass one that matches.
    # Let's write a small helper or test directly using one of the actual items.
    # If DEPRECATED_SINGLE_DASH_ARGS contains '-df', then passing '-df' makes `arg` == '-df' which is in DEPRECATED_SINGLE_DASH_ARGS.
    # Then remapped_deprecated_args.append('-df'), and argv[index] = f"--df".
    res = parse_args([dep_arg])
    assert "remapped_deprecated_args" in res
    assert dep_arg in res["remapped_deprecated_args"]


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
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--float-to-top", "--dont-float-to-top"])
    assert exc_info.value.code == "Can't set both --float-to-top and --dont-float-to-top."


def test_parse_args_multi_line_output_digit():
    res = parse_args(["--multi-line", "3"])
    assert res.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT


def test_parse_args_multi_line_output_string():
    res = parse_args(["--multi-line", "VERTICAL_HANGING_INDENT"])
    assert res.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT
