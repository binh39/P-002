# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

from isort.wrap_modes import noqa

def test_noqa_with_comments_within_line_length():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": ["# comment"],
        "comment_prefix": "  #",
        "line_length": 80,
    }
    # len(retval) = len("import os") = 9
    # len(comment_prefix) = 3 ("  #")
    # len(comment_str) = 9 ("# comment")
    # 9 + 3 + 1 + 9 = 22 <= 80 -> triggers line 253
    result = noqa(**interface)
    assert result == "import os  # # comment"


def test_noqa_with_comments_exceeds_line_length_with_noqa():
    interface = {
        "statement": "import " + "a" * 70,
        "imports": ["os"],
        "comments": ["NOQA"],
        "comment_prefix": " #",
        "line_length": 40,
    }
    # Exceeds line length, but "NOQA" is in comments -> triggers line 255
    result = noqa(**interface)
    assert result == f"{interface['statement']}os # NOQA"


def test_noqa_with_comments_exceeds_line_length_without_noqa():
    interface = {
        "statement": "import " + "a" * 70,
        "imports": ["os"],
        "comments": ["custom"],
        "comment_prefix": " #",
        "line_length": 40,
    }
    # Exceeds line length, "NOQA" not in comments -> triggers line 256
    result = noqa(**interface)
    assert result == f"{interface['statement']}os # NOQA custom"


def test_noqa_without_comments_within_line_length():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 80,
    }
    # No comments, len(retval) <= line_length -> triggers line 259
    result = noqa(**interface)
    assert result == "import os"


def test_noqa_without_comments_exceeds_line_length():
    interface = {
        "statement": "import " + "a" * 70,
        "imports": ["os"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 40,
    }
    # No comments, len(retval) > line_length -> triggers line 260
    result = noqa(**interface)
    assert result == f"{interface['statement']}os # NOQA"
