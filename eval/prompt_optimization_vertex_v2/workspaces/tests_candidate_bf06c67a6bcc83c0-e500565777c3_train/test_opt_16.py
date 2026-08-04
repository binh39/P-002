# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

import pytest
from isort.wrap_modes import noqa


def test_noqa_with_comments_fits_line_length():
    interface = {
        "statement": "import ",
        "imports": ["a", "b"],
        "comments": ["comment1"],
        "comment_prefix": " #",
        "line_length": 80,
    }
    result = noqa(**interface)
    assert result == "import a, b # comment1"


def test_noqa_with_comments_exceeds_but_has_noqa():
    interface = {
        "statement": "import ",
        "imports": ["very_long_import_name_a", "very_long_import_name_b"],
        "comments": ["NOQA"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    result = noqa(**interface)
    assert result == "import very_long_import_name_a, very_long_import_name_b # NOQA"


def test_noqa_with_comments_exceeds_and_lacks_noqa():
    interface = {
        "statement": "import ",
        "imports": ["very_long_import_name_a", "very_long_import_name_b"],
        "comments": ["comment1"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    result = noqa(**interface)
    assert result == "import very_long_import_name_a, very_long_import_name_b # NOQA comment1"


def test_noqa_without_comments_fits_line_length():
    interface = {
        "statement": "import ",
        "imports": ["a"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 80,
    }
    result = noqa(**interface)
    assert result == "import a"


def test_noqa_without_comments_exceeds_line_length():
    interface = {
        "statement": "import ",
        "imports": ["very_long_import_name_a", "very_long_import_name_b"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 20,
    }
    result = noqa(**interface)
    assert result == "import very_long_import_name_a, very_long_import_name_b # NOQA"
