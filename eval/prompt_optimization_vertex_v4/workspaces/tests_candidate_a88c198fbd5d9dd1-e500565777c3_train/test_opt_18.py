# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

from isort.wrap_modes import noqa


def test_noqa_wrap_mode_with_comments_fitting_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": ["comment"],
        "comment_prefix": " #",
        "line_length": 30,
    }
    # retval = "import os" (len 9)
    # comment_str = "comment" (len 7)
    # len(retval) + len(comment_prefix) + 1 + len(comment_str) = 9 + 2 + 1 + 7 = 19 <= 30
    res = noqa(**interface)
    assert res == "import os # comment"


def test_noqa_wrap_mode_with_comments_containing_noqa():
    interface = {
        "statement": "import ",
        "imports": ["os, sys, math, collections, itertools, functools"],
        "comments": ["NOQA", "extra"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # retval and comments are long so line length check fails,
    # but "NOQA" is in comments.
    res = noqa(**interface)
    assert res == f"{interface['statement']}{interface['imports'][0]} # NOQA extra"


def test_noqa_wrap_mode_with_comments_not_fitting_and_no_noqa():
    interface = {
        "statement": "import ",
        "imports": ["os, sys, math, collections, itertools, functools"],
        "comments": ["extra"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # comments don't fit and "NOQA" not in comments -> inserts NOQA before comment_str
    res = noqa(**interface)
    assert res == f"{interface['statement']}{interface['imports'][0]} # NOQA extra"


def test_noqa_wrap_mode_without_comments_fitting_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # no comments, len(retval) = 9 <= 20 -> returns retval
    res = noqa(**interface)
    assert res == "import os"


def test_noqa_wrap_mode_without_comments_exceeding_line():
    interface = {
        "statement": "import ",
        "imports": ["os, sys, math, collections, itertools, functools"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # no comments, len(retval) > 20 -> returns retval + comment_prefix + NOQA
    res = noqa(**interface)
    assert res == f"{interface['statement']}{interface['imports'][0]} # NOQA"
