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
        "comment_prefix": "  #",
        "line_length": 100,
    }
    # retval = "import os, sys" (len = 14)
    # comment_str = "comment1" (len = 8)
    # len(retval) + len(comment_prefix) + 1 + len(comment_str) = 14 + 3 + 1 + 8 = 26 <= 100
    # Executes line 253
    result = noqa(**interface)
    assert result == "import os, sys  # comment1"

def test_noqa_wrap_mode_with_comments_long_line_containing_noqa():
    interface = {
        "statement": "import " + "a" * 80,
        "imports": ["os"],
        "comments": ["NOQA", "comment2"],
        "comment_prefix": "  #",
        "line_length": 50,
    }
    # Line length exceeded, but "NOQA" in interface["comments"] -> executes line 255
    result = noqa(**interface)
    assert "NOQA" in result
    assert "comment2" in result

def test_noqa_wrap_mode_with_comments_long_line_missing_noqa():
    interface = {
        "statement": "import " + "a" * 80,
        "imports": ["os"],
        "comments": ["comment2"],
        "comment_prefix": "  #",
        "line_length": 50,
    }
    # Line length exceeded, "NOQA" not in comments -> executes line 256
    result = noqa(**interface)
    assert "NOQA" in result
    assert "comment2" in result

def test_noqa_wrap_mode_no_comments_short_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 50,
    }
    # No comments, len(retval) <= line_length -> executes line 259
    result = noqa(**interface)
    assert result == "import os"

def test_noqa_wrap_mode_no_comments_long_line():
    interface = {
        "statement": "import " + "a" * 80,
        "imports": ["os"],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 50,
    }
    # No comments, len(retval) > line_length -> executes line 260
    result = noqa(**interface)
    assert result.endswith("  # NOQA")
