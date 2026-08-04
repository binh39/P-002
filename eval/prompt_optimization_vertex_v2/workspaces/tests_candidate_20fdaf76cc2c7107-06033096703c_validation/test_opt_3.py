# file: src\sample_repo\isort\isort\comments.py:12-29
# asked: {"lines": [12, 13, 14, 15, 16, 17, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}
# gained: {"lines": [12, 13, 14, 15, 16, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}

from isort.comments import add_to_line


def test_add_to_line_removed_true():
    # If removed is True, should return parsed original string (removing any existing comments)
    original = "import os  # noqa"
    result = add_to_line(comments=["# comment"], original_string=original, removed=True)
    assert result == "import os  "


def test_add_to_line_no_comments():
    # If comments is None or empty, should return original_string unchanged
    original = "import sys"
    assert add_to_line(comments=None, original_string=original, removed=False) == original
    assert add_to_line(comments=[], original_string=original, removed=False) == original


def test_add_to_line_with_unique_comments():
    # Should deduplicate comments and append them using comment_prefix and '; '
    original = "import math"
    comments = ["# first", "# second", "# first"]
    result = add_to_line(
        comments=comments,
        original_string=original,
        removed=False,
        comment_prefix="  #",
    )
    assert result == "import math  # # first; # second"
