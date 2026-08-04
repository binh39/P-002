# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

from typing import Any
from isort.wrap_modes import noqa


def test_noqa_wrap_mode_with_comments_fitting_line_length() -> None:
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": ["comment"],
        "comment_prefix": " #",
        "line_length": 80,
    }
    result = noqa(**interface)
    assert result == "import os # comment"


def test_noqa_wrap_mode_with_comments_exceeding_line_length_with_noqa() -> None:
    interface = {
        "statement": "import ",
        "imports": ["os", "sys"],
        "comments": ["NOQA", "custom"],
        "comment_prefix": " #",
        "line_length": 10,
    }
    result = noqa(**interface)
    assert result == "import os, sys # NOQA custom"


def test_noqa_wrap_mode_with_comments_exceeding_line_length_without_noqa() -> None:
    interface = {
        "statement": "import ",
        "imports": ["os", "sys"],
        "comments": ["custom"],
        "comment_prefix": " #",
        "line_length": 10,
    }
    result = noqa(**interface)
    assert result == "import os, sys # NOQA custom"


def test_noqa_wrap_mode_without_comments_fitting_line_length() -> None:
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 80,
    }
    result = noqa(**interface)
    assert result == "import os"


def test_noqa_wrap_mode_without_comments_exceeding_line_length() -> None:
    interface = {
        "statement": "import ",
        "imports": ["os", "sys"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 5,
    }
    result = noqa(**interface)
    assert result == "import os, sys # NOQA"
