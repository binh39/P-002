# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

import pytest
from isort.wrap_modes import noqa


def test_noqa_wrap_mode_with_comments_fits_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": ["comment"],
        "comment_prefix": " #",
        "line_length": 30,
    }
    # len("import os") = 9
    # len(" #") = 2
    # len(" ") = 1
    # len("comment") = 7
    # Total = 9 + 2 + 1 + 7 = 19 <= 30
    result = noqa(**interface)
    assert result == "import os # comment"


def test_noqa_wrap_mode_with_comments_exceeds_line_has_noqa():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "math"],
        "comments": ["NOQA", "extra"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # Exceeds length, but "NOQA" is in comments
    result = noqa(**interface)
    assert result == "import os, sys, math # NOQA extra"


def test_noqa_wrap_mode_with_comments_exceeds_line_no_noqa():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "math"],
        "comments": ["some_comment"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # Exceeds length, "NOQA" not in comments -> inserts NOQA
    result = noqa(**interface)
    assert result == "import os, sys, math # NOQA some_comment"


def test_noqa_wrap_mode_no_comments_fits_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # No comments, length <= line_length
    result = noqa(**interface)
    assert result == "import os"


def test_noqa_wrap_mode_no_comments_exceeds_line():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "math", "itertools"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # No comments, length > line_length -> appends comment_prefix + " NOQA"
    result = noqa(**interface)
    assert result == "import os, sys, math, itertools # NOQA"
