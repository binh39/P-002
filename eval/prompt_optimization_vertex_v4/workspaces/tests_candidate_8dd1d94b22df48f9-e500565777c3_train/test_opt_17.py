# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import DEPRECATED_SINGLE_DASH_ARGS, parse_args
from isort.wrap_modes import WrapModes


def test_parse_args_all_branches():
    # 1. Default argv (argv=None)
    res_default = parse_args([])
    assert isinstance(res_default, dict)

    # 2. remapped_deprecated_args branch & deprecated single dash args
    non_val_dep_args = ['ds', 'ac', 'ot', 'df', 'dt']
    chosen_dep = None
    for d in non_val_dep_args:
        if f"-{d}" in DEPRECATED_SINGLE_DASH_ARGS:
            chosen_dep = f"-{d}"
            break
    if not chosen_dep and DEPRECATED_SINGLE_DASH_ARGS:
        chosen_dep = list(DEPRECATED_SINGLE_DASH_ARGS)[0]

    if chosen_dep:
        res_dep = parse_args([chosen_dep])
        assert "remapped_deprecated_args" in res_dep

    # 3. dont_order_by_type
    res_order = parse_args(["--dont-order-by-type"])
    assert res_order.get("order_by_type") is False
    assert "dont_order_by_type" not in res_order

    # 4. dont_follow_links
    res_links = parse_args(["--dont-follow-links"])
    assert res_links.get("follow_links") is False
    assert "dont_follow_links" not in res_links

    # 5. dont_float_to_top (else branch: float_to_top = False)
    res_float1 = parse_args(["--dont-float-to-top"])
    assert res_float1.get("float_to_top") is False
    assert "dont_float_to_top" not in res_float1

    # 6. dont_float_to_top with float_to_top already set (sys.exit branch)
    with pytest.raises(SystemExit):
        parse_args(["--float-to-top", "--dont-float-to-top"])

    # 7. multi_line_output numeric digit string (e.g. "3") via short option '-m'
    res_ml_digit = parse_args(["-m", "3"])
    assert res_ml_digit.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT

    # 8. multi_line_output non-digit string (e.g. "VERTICAL_HANGING_INDENT") via short option '-m'
    res_ml_str = parse_args(["-m", "VERTICAL_HANGING_INDENT"])
    assert res_ml_str.get("multi_line_output") == WrapModes.VERTICAL_HANGING_INDENT
