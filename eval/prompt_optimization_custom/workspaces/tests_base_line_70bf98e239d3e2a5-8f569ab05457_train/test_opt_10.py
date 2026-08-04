# file: src\sample_repo\isort\isort\main.py:928-959
# asked: {"lines": [928, 929, 930, 931, 932, 933, 934, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 951, 952, 953, 954, 955, 957, 959], "branches": [[931, 932], [931, 936], [932, 931], [932, 933], [938, 939], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [948, 951], [953, 954], [953, 959], [954, 955], [954, 957]]}
# gained: {"lines": [928, 929, 930, 931, 932, 936, 937, 938, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 952, 953, 959], "branches": [[931, 932], [931, 936], [932, 931], [938, 940], [940, 941], [940, 943], [943, 944], [943, 946], [946, 947], [946, 952], [948, 949], [953, 959]]}

import sys
import pytest
from unittest.mock import patch
from isort.main import parse_args

# Mocking the DEPRECATED_SINGLE_DASH_ARGS for testing
DEPRECATED_SINGLE_DASH_ARGS = {'-ac', '-af', '-ca', '-cs', '-df', '-ds', '-dt', '-fas', '-fass', '-ff', '-fgw', '-fss', '-lai', '-lbt', '-le', '-ls', '-nis', '-nlb', '-ot', '-rr', '-sd', '-sg', '-sl', '-sp', '-tc', '-wl', '-ws'}

@pytest.fixture
def reset_sys_argv():
    original_argv = sys.argv.copy()
    yield
    sys.argv = original_argv


def test_parse_args_with_dont_order_by_type(reset_sys_argv):
    sys.argv = ['script_name', '--dont-order-by-type']
    expected = {
        'order_by_type': False,
    }
    result = parse_args()
    assert result.get('order_by_type') == expected['order_by_type']

def test_parse_args_with_dont_follow_links(reset_sys_argv):
    sys.argv = ['script_name', '--dont-follow-links']
    expected = {
        'follow_links': False,
    }
    result = parse_args()
    assert result.get('follow_links') == expected['follow_links']

def test_parse_args_with_dont_float_to_top(reset_sys_argv):
    sys.argv = ['script_name', '--dont-float-to-top', '--float-to-top']
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        parse_args()
    assert str(pytest_wrapped_e.value) == "Can't set both --float-to-top and --dont-float-to-top."


