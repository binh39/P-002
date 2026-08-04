# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

from isort.wrap_modes import noqa


def test_noqa_wrap_mode_with_comments_fits_line_length():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": ["comment1"],
        "comment_prefix": " #",
        "line_length": 30,
    }
    result = noqa(**interface)
    assert result == "import os # comment1"


def test_noqa_wrap_mode_with_comments_noqa_already_present():
    interface = {
        "statement": "import " + "a" * 40,
        "imports": ["os"],
        "comments": ["NOQA", "comment1"],
        "comment_prefix": " #",
        "line_length": 30,
    }
    result = noqa(**interface)
    assert result == f"import {'a' * 40}os # NOQA comment1"


def test_noqa_wrap_mode_with_comments_noqa_added():
    interface = {
        "statement": "import " + "a" * 40,
        "imports": ["os"],
        "comments": ["comment1"],
        "comment_prefix": " #",
        "line_length": 30,
    }
    result = noqa(**interface)
    assert result == f"import {'a' * 40}os # NOQA comment1"


def test_noqa_wrap_mode_without_comments_fits_line_length():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 30,
    }
    result = noqa(**interface)
    assert result == "import os"


def test_noqa_wrap_mode_without_comments_exceeds_line_length():
    interface = {
        "statement": "import " + "a" * 40,
        "imports": ["os"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 30,
    }
    result = noqa(**interface)
    assert result == f"import {'a' * 40}os # NOQA"
