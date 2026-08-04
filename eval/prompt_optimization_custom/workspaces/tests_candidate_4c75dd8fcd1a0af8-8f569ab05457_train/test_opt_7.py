# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 936, 937, 938, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}

import pytest
import sys
from isort.main import parse_args
from isort.wrap_modes import WrapModes

# Mocking the _build_arg_parser function to return a parser with specific arguments
def mock_build_arg_parser():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dont-order-by-type', action='store_true')
    parser.add_argument('--dont-follow-links', action='store_true')
    parser.add_argument('--dont-float-to-top', action='store_true')
    parser.add_argument('--float-to-top', action='store_true')
    parser.add_argument('--multi-line-output', type=str)
    return parser

# Patching the _build_arg_parser function in the module
@pytest.fixture(autouse=True)
def patch_build_arg_parser(monkeypatch):
    monkeypatch.setattr('isort.main._build_arg_parser', mock_build_arg_parser)


def test_parse_args_dont_order_by_type():
    args = parse_args(['--dont-order-by-type'])
    assert args['order_by_type'] is False

def test_parse_args_dont_follow_links():
    args = parse_args(['--dont-follow-links'])
    assert args['follow_links'] is False

def test_parse_args_dont_float_to_top_with_float_to_top():
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        parse_args(['--dont-float-to-top', '--float-to-top'])
    assert str(pytest_wrapped_e.value) == "Can't set both --float-to-top and --dont-float-to-top."

def test_parse_args_dont_float_to_top_without_float_to_top():
    args = parse_args(['--dont-float-to-top'])
    assert 'float_to_top' in args
    assert args['float_to_top'] is False

def test_parse_args_multi_line_output_digit():
    args = parse_args(['--multi-line-output', '1'])
    assert args['multi_line_output'] == WrapModes(1)

def test_parse_args_multi_line_output_non_digit():
    args = parse_args(['--multi-line-output', '0'])  # Using a valid enum key
    assert args['multi_line_output'] == WrapModes(0)

def test_parse_args_multi_line_output_invalid():
    with pytest.raises(KeyError):
        parse_args(['--multi-line-output', 'invalid_mode'])  # Invalid mode should raise KeyError
