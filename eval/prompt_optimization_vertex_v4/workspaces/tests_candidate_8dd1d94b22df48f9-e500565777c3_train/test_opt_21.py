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
    # len(retval) = len("import os, sys") = 14
    # comment_prefix = " #" (len 2)
    # comment_str = "comment1" (len 8)
    # Total: 14 + 2 + 1 + 8 = 25 <= 80 (True)
    result = noqa(**interface)
    assert result == "import os, sys # comment1"


def test_noqa_wrap_mode_with_comments_long_line_has_noqa():
    interface = {
        "statement": "import " + "a, " * 30,
        "imports": ["os"],
        "comments": ["NOQA", "extra"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # Line length exceeds, but "NOQA" in comments is True -> returns f"{retval}{comment_prefix} {comment_str}"
    result = noqa(**interface)
    assert "NOQA" in result
    assert "extra" in result


def test_noqa_wrap_mode_with_comments_long_line_no_noqa():
    interface = {
        "statement": "import " + "a, " * 30,
        "imports": ["os"],
        "comments": ["extra"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # Line length exceeds, "NOQA" not in comments -> returns f"{retval}{comment_prefix} NOQA {comment_str}"
    result = noqa(**interface)
    assert "NOQA" in result
    assert "extra" in result


def test_noqa_wrap_mode_no_comments_short_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 80,
    }
    # interface["comments"] is empty
    # len(retval) = 10 <= 80 -> returns retval (line 259)
    result = noqa(**interface)
    assert result == "import os"


def test_noqa_wrap_mode_no_comments_long_line():
    interface = {
        "statement": "import " + "a, " * 30,
        "imports": ["os"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # interface["comments"] is empty
    # len(retval) > 20 -> returns f"{retval}{comment_prefix} NOQA" (line 260)
    result = noqa(**interface)
    assert result.endswith(" # NOQA")
