# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

import pytest
from isort.wrap_modes import noqa


def test_noqa_with_comments_fitting_line_length():
    interface = {
        "statement": "import a, ",
        "imports": ["b"],
        "comments": ["custom"],
        "comment_prefix": " #",
        "line_length": 30,
    }
    # retval = "import a, b" (len 11)
    # comment_str = "custom" (len 6)
    # len(retval) + len(comment_prefix) + 1 + len(comment_str) = 11 + 2 + 1 + 6 = 20 <= 30
    res = noqa(**interface)
    assert res == "import a, b # custom"


def test_noqa_with_comments_exceeding_line_length_but_has_noqa():
    interface = {
        "statement": "import a, ",
        "imports": ["b"],
        "comments": ["NOQA", "custom"],
        "comment_prefix": " #",
        "line_length": 10,
    }
    # Exceeds line_length, but 'NOQA' in interface["comments"]
    res = noqa(**interface)
    assert res == "import a, b # NOQA custom"


def test_noqa_with_comments_exceeding_line_length_without_noqa():
    interface = {
        "statement": "import a, ",
        "imports": ["b"],
        "comments": ["custom"],
        "comment_prefix": " #",
        "line_length": 10,
    }
    # Exceeds line_length, 'NOQA' not in comments -> prepends 'NOQA'
    res = noqa(**interface)
    assert res == "import a, b # NOQA custom"


def test_noqa_without_comments_fitting_line_length():
    interface = {
        "statement": "import a, ",
        "imports": ["b"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # retval = "import a, b" (len 11 <= 20)
    res = noqa(**interface)
    assert res == "import a, b"


def test_noqa_without_comments_exceeding_line_length():
    interface = {
        "statement": "import a, ",
        "imports": ["b"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 5,
    }
    # retval = "import a, b" (len 11 > 5) -> appends " # NOQA"
    res = noqa(**interface)
    assert res == "import a, b # NOQA"
