# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

from isort.wrap_modes import noqa

def test_noqa_wrap_mode_with_comments_short_line():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys"],
        "comments": ["comment1"],
        "comment_prefix": " #",
        "line_length": 50,
    }
    # len(retval) = len("import os, sys") = 14
    # len(" #") = 2, len(" ") = 1, len("comment1") = 8
    # total = 14 + 2 + 1 + 8 = 25 <= 50 (line_length) -> branch line 253
    result = noqa(**interface)
    assert result == "import os, sys # comment1"


def test_noqa_wrap_mode_with_comments_long_line_has_noqa():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "math", "collections", "itertools"],
        "comments": ["NOQA", "comment2"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # len(retval) > line_length and "NOQA" in interface["comments"] -> branch line 255
    result = noqa(**interface)
    assert "NOQA" in result
    assert result.endswith("NOQA comment2")


def test_noqa_wrap_mode_with_comments_long_line_no_noqa():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "math", "collections", "itertools"],
        "comments": ["comment2"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # len(retval) > line_length and "NOQA" not in interface["comments"] -> branch line 256
    result = noqa(**interface)
    assert "NOQA" in result
    assert "NOQA comment2" in result


def test_noqa_wrap_mode_no_comments_short_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # interface["comments"] is empty, len(retval) <= line_length -> branch line 259
    result = noqa(**interface)
    assert result == "import os"


def test_noqa_wrap_mode_no_comments_long_line():
    interface = {
        "statement": "import ",
        "imports": ["os", "sys", "math", "collections", "itertools"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # interface["comments"] is empty, len(retval) > line_length -> branch line 260
    result = noqa(**interface)
    assert result.endswith(" # NOQA")
