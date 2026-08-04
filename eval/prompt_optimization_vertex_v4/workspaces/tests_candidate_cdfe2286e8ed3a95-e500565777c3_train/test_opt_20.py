# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

from isort.wrap_modes import noqa


def test_noqa_wrap_mode_with_comments_short_line():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys"],
        "comments": ["# comment"],
        "comment_prefix": "  #",
        "line_length": 100,
    }
    # length check <= line_length should be True
    # len("import os, sys") + len("  #") + 1 + len("# comment") = 14 + 3 + 1 + 9 = 27 <= 100
    res = noqa(**interface)
    assert res == "import os, sys  # # comment"


def test_noqa_wrap_mode_with_comments_noqa_in_comments():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "math", "collections"],
        "comments": ["NOQA", "extra"],
        "comment_prefix": "  #",
        "line_length": 20,
    }
    # length check <= line_length will be False
    # "NOQA" in interface["comments"] is True
    res = noqa(**interface)
    assert res == "import os, sys, math, collections  # NOQA extra"


def test_noqa_wrap_mode_with_comments_noqa_not_in_comments():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "math", "collections"],
        "comments": ["extra"],
        "comment_prefix": "  #",
        "line_length": 20,
    }
    # length check <= line_length will be False
    # "NOQA" in interface["comments"] is False
    # should insert "NOQA" between comment_prefix and comment_str
    res = noqa(**interface)
    assert res == "import os, sys, math, collections  # NOQA extra"


def test_noqa_wrap_mode_without_comments_short_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 50,
    }
    # interface["comments"] is empty/false
    # len(retval) <= line_length (10 <= 50) is True
    res = noqa(**interface)
    assert res == "import os"


def test_noqa_wrap_mode_without_comments_long_line():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "math", "collections"],
        "comments": [],
        "comment_prefix": "  #",
        "line_length": 10,
    }
    # interface["comments"] is empty/false
    # len(retval) <= line_length is False
    res = noqa(**interface)
    assert res == "import os, sys, math, collections  # NOQA"
