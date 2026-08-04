# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

import pytest
from isort.wrap_modes import noqa

def test_noqa_wrap_mode_with_comments_fitting_line_length():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": ["# comment"],
        "comment_prefix": "  #",
        "line_length": 50,
    }
    # len(retval) = len("import os") = 9
    # len(comment_prefix) = 3 ("  #")
    # len(comment_str) = 9 ("# comment")
    # 9 + 3 + 1 + 9 = 22 <= 50 (fits)
    result = noqa(**interface)
    assert result == "import os  # # comment"

def test_noqa_wrap_mode_with_comments_exceeding_but_has_noqa():
    interface = {
        "statement": "import ",
        "imports": ["a" * 40],
        "comments": ["# comment", "NOQA"],
        "comment_prefix": "  #",
        "line_length": 20,
    }
    # Doesn't fit in line_length, but "NOQA" is in interface["comments"]
    result = noqa(**interface)
    assert result == f"import {'a' * 40}  # # comment NOQA"

def test_noqa_wrap_mode_with_comments_exceeding_without_noqa():
    interface = {
        "statement": "import ",
        "imports": ["a" * 40],
        "comments": ["# comment"],
        "comment_prefix": "  #",
        "line_length": 20,
    }
    # Doesn't fit, "NOQA" not in comments -> inserts NOQA in between
    result = noqa(**interface)
    assert result == f"import {'a' * 40}  # NOQA # comment"

def test_noqa_wrap_mode_no_comments_fitting_line_length():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 20,
    }
    # No comments, retval length <= line_length
    result = noqa(**interface)
    assert result == "import os"

def test_noqa_wrap_mode_no_comments_exceeding_line_length():
    interface = {
        "statement": "import ",
        "imports": ["a" * 30],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 20,
    }
    # No comments, retval length > line_length -> appends comment_prefix + NOQA
    result = noqa(**interface)
    assert result == f"import {'a' * 30}  # NOQA"
