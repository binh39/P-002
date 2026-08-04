# file: src\sample_repo\isort\isort\wrap_modes.py:243-260
# asked: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}
# gained: {"lines": [243, 244, 245, 246, 247, 248, 250, 251, 253, 254, 255, 256, 258, 259, 260], "branches": [[248, 249], [248, 258], [249, 253], [249, 254], [254, 255], [254, 256], [258, 259], [258, 260]]}

from isort.wrap_modes import noqa


def test_noqa_wrap_mode_with_comments_within_line_length():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": ["# comment"],
        "comment_prefix": " #",
        "line_length": 50,
    }
    result = noqa(**interface)
    # len("import os") + len(" #") + 1 + len("# comment") = 9 + 2 + 1 + 9 = 21 <= 50
    assert result == "import os # # comment"


def test_noqa_wrap_mode_with_comments_exceeding_line_length_with_noqa():
    interface = {
        "statement": "import ",
        "imports": ["very_long_module_name_that_exceeds_normal_lengths"],
        "comments": ["NOQA", "# extra"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    result = noqa(**interface)
    # Exceeds line length, but "NOQA" is in comments -> returns without inserting extra NOQA
    assert "NOQA" in result
    assert "NOQA NOQA" not in result


def test_noqa_wrap_mode_with_comments_exceeding_line_length_without_noqa():
    interface = {
        "statement": "import ",
        "imports": ["very_long_module_name_that_exceeds_normal_lengths"],
        "comments": ["# comment"],
        "comment_prefix": " #",
        "line_length": 20,
    }
    result = noqa(**interface)
    # Exceeds line length, "NOQA" not in comments -> inserts NOQA in between
    assert "NOQA" in result
    assert result.endswith(" # NOQA # comment")


def test_noqa_wrap_mode_without_comments_within_line_length():
    interface = {
        "statement": "import ",
        "imports": ["os"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 50,
    }
    result = noqa(**interface)
    # No comments, len(retval) <= line_length
    assert result == "import os"


def test_noqa_wrap_mode_without_comments_exceeding_line_length():
    interface = {
        "statement": "import ",
        "imports": ["very_long_module_name_that_exceeds_normal_lengths"],
        "comments": [],
        "comment_prefix": " #",
        "line_length": 10,
    }
    result = noqa(**interface)
    # No comments, len(retval) > line_length -> appends comment_prefix and NOQA
    assert result.endswith(" # NOQA")
