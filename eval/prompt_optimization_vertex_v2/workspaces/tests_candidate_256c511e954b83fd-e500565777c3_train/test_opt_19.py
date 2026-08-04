# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

from isort.wrap_modes import noqa


def test_noqa_wrap_mode_with_comments_fits_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": ["comment1"],
        "comment_prefix": " #",
        "line_length": 50,
    }
    # retval = "import os", len = 9
    # comment_str = "comment1", len = 8
    # comment_prefix = " #", len = 2
    # 9 + 2 + 1 + 8 = 20 <= 50 (fits)
    result = noqa(**interface)
    assert result == "import os # comment1"


def test_noqa_wrap_mode_with_comments_exceeds_but_has_noqa():
    interface = {
        "statement": "import ",
        "imports": ["a_very_long_import_name_to_exceed_length"],
        "comments": ["NOQA"],
        "comment_prefix": " #",
        "line_length": 15,
    }
    # retval length > 15, comments has "NOQA"
    result = noqa(**interface)
    assert result == "import a_very_long_import_name_to_exceed_length # NOQA"


def test_noqa_wrap_mode_with_comments_exceeds_and_missing_noqa():
    interface = {
        "statement": "import ",
        "imports": ["a_very_long_import_name_to_exceed_length"],
        "comments": ["some_comment"],
        "comment_prefix": " #",
        "line_length": 15,
    }
    # retval length > 15, comments lacks "NOQA"
    result = noqa(**interface)
    assert result == "import a_very_long_import_name_to_exceed_length # NOQA some_comment"


def test_noqa_wrap_mode_without_comments_fits_line():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 20,
    }
    # retval = "import os", len = 9 <= 20
    result = noqa(**interface)
    assert result == "import os"


def test_noqa_wrap_mode_without_comments_exceeds_line():
    interface = {
        "statement": "import ",
        "imports": ["a_very_long_import_name_to_exceed_length"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 10,
    }
    # retval length > 10, no comments
    result = noqa(**interface)
    assert result == "import a_very_long_import_name_to_exceed_length # NOQA"
