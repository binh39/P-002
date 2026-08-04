# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 256, 258, 259], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 256], [258, 259]]}

import pytest

# Assuming the _wrap_mode decorator is defined in the same module as the function to be tested
from isort.wrap_modes import noqa

@pytest.mark.parametrize("interface, expected", [
    (
        {
            "imports": ["import os"],
            "statement": "print('Hello World')",
            "comments": ["This is a comment"],
            "comment_prefix": "#",
            "line_length": 80
        },
        "print('Hello World')import os# This is a comment"
    ),
    (
        {
            "imports": ["import sys"],
            "statement": "print('Hello World')",
            "comments": ["NOQA"],
            "comment_prefix": "#",
            "line_length": 80
        },
        "print('Hello World')import sys# NOQA"
    ),
    (
        {
            "imports": ["import json"],
            "statement": "print('Hello World')",
            "comments": [],
            "comment_prefix": "#",
            "line_length": 80
        },
        "print('Hello World')import json"
    ),
    (
        {
            "imports": ["import math"],
            "statement": "print('Hello World')",
            "comments": ["This is a long comment that exceeds the line length"],
            "comment_prefix": "#",
            "line_length": 50
        },
        "print('Hello World')import math# NOQA This is a long comment that exceeds the line length"
    ),
])
def test_noqa(interface, expected):
    result = noqa(**interface)
    assert result == expected

@pytest.mark.parametrize("interface, expected", [
    (
        {
            "imports": ["import os"],
            "statement": "print('Hello World')",
            "comments": ["This is a comment"],
            "comment_prefix": "#",
            "line_length": 50
        },
        "print('Hello World')import os# This is a comment"
    ),
])
def test_noqa_with_long_comment(interface, expected):
    result = noqa(**interface)
    assert result == expected

@pytest.mark.parametrize("interface, expected", [
    (
        {
            "imports": ["import os"],
            "statement": "print('Hello World')",
            "comments": ["This is a comment"],
            "comment_prefix": "#",
            "line_length": 30
        },
        "print('Hello World')import os# NOQA This is a comment"
    ),
])
def test_noqa_with_exceeding_length(interface, expected):
    result = noqa(**interface)
    assert result == expected
