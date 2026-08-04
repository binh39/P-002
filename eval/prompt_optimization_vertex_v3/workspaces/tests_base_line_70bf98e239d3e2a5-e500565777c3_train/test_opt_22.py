# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

import pytest
from isort.wrap_modes import noqa

def test_noqa_wrap_mode_with_comments_short_line():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys"],
        "comments": ["comment1"],
        "comment_prefix": " #",
        "line_length": 80,
    }
    # retval = "import os, sys", len = 14
    # comment_prefix = " #", len = 2
    # comment_str = "comment1", len = 8
    # total len = 14 + 2 + 1 + 8 = 25 <= 80
    result = noqa(**interface)
    assert result == "import os, sys # comment1"

def test_noqa_wrap_mode_with_comments_long_line_containing_noqa():
    interface = {
        "statement": "import " + "a, " * 30,
        "imports": ["b"],
        "comments": ["NOQA", "other"],
        "comment_prefix": " #",
        "line_length": 40,
    }
    # line length exceeded, but "NOQA" is in interface["comments"]
    result = noqa(**interface)
    assert "NOQA" in result
    assert "# NOQA other" in result

def test_noqa_wrap_mode_with_comments_long_line_without_noqa():
    interface = {
        "statement": "import " + "a, " * 30,
        "imports": ["b"],
        "comments": ["other"],
        "comment_prefix": " #",
        "line_length": 40,
    }
    # line length exceeded, "NOQA" not in comments -> inserts NOQA
    result = noqa(**interface)
    assert "# NOQA other" in result

def test_noqa_wrap_mode_without_comments_short_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 80,
    }
    # len(retval) <= line_length
    result = noqa(**interface)
    assert result == "import os"

def test_noqa_wrap_mode_without_comments_long_line():
    interface = {
        "statement": "import " + "a, " * 30,
        "imports": ["b"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 40,
    }
    # len(retval) > line_length, no comments -> appends " # NOQA"
    result = noqa(**interface)
    assert result.endswith(" # NOQA")
