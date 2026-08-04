# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
from isort.main import parse_args
from isort.wrap_modes import WrapModes


def test_parse_args_deprecated_args():
    # Test DEPRECATED_SINGLE_DASH_ARGS remapping (e.g., '-ac')
    # Depending on how the parser handles it, let's pass a valid deprecated single dash arg if any exist,
    # or test with one from DEPRECATED_SINGLE_DASH_ARGS without the leading dash if the code checks `arg in DEPRECATED_SINGLE_DASH_ARGS`.
    # Wait, DEPRECATED_SINGLE_DASH_ARGS contains items starting with '-' (e.g. '-ac').
    # Let's check what DEPRECATED_SINGLE_DASH_ARGS has. It has strings starting with '-'.
    # If argv has '-ac', `arg in DEPRECATED_SINGLE_DASH_ARGS` matches, and it does `argv[index] = f"-{arg}"` which becomes `--ac` or similar? 
    # Wait, if arg is '-ac', f"-{arg}" becomes '--ac'. Let's test with a valid deprecated arg like 'ac' or '-ac'.
    # Actually let's inspect DEPRECATED_SINGLE_DASH_ARGS: {'-ac', ...}
    # If argv=['-ac'], arg is '-ac' which is in DEPRECATED_SINGLE_DASH_ARGS.
    # remapped_deprecated_args.append('-ac'), argv[index] = '--ac'.
    res = parse_args(['-ac', '.'])
    assert 'remapped_deprecated_args' in res


def test_parse_args_dont_order_by_type():
    res = parse_args(['--dont-order-by-type', '.'])
    assert res.get('order_by_type') is False
    assert 'dont_order_by_type' not in res


def test_parse_args_dont_follow_links():
    res = parse_args(['--dont-follow-links', '.'])
    assert res.get('follow_links') is False
    assert 'dont_follow_links' not in res


def test_parse_args_dont_float_to_top_else():
    # Test --dont-float-to-top when float_to_top is not set (goes to else branch: arguments["float_to_top"] = False)
    res = parse_args(['--dont-float-to-top', '.'])
    assert res.get('float_to_top') is False


def test_parse_args_dont_float_to_top_conflict():
    # Test --dont-float-to-top when --float-to-top is also set (calls sys.exit)
    with pytest.raises(SystemExit) as excinfo:
        parse_args(['--float-to-top', '--dont-float-to-top', '.'])
    assert "Can't set both --float-to-top and --dont-float-to-top." in str(excinfo.value)


def test_parse_args_multi_line_output_digit():
    res = parse_args(['--multi-line', '3', '.'])
    assert res.get('multi_line_output') == WrapModes.VERTICAL_HANGING_INDENT


def test_parse_args_multi_line_output_string():
    res = parse_args(['--multi-line', 'VERTICAL_HANGING_INDENT', '.'])
    assert res.get('multi_line_output') == WrapModes.VERTICAL_HANGING_INDENT
