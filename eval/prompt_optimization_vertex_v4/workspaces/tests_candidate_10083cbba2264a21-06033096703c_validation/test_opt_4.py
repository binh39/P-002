# file: src\sample_repo\isort\isort\comments.py:12-29
# asked: {"lines": [12, 13, 14, 15, 16, 17, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}
# gained: {"lines": [12, 13, 14, 15, 16, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}

import pytest
from isort.comments import add_to_line


def test_add_to_line_removed():
    # Covers line 19-20 (removed=True)
    result = add_to_line(
        comments=["# comment"],
        original_string="x = 1  # comment",
        removed=True,
        comment_prefix="#",
    )
    assert result == "x = 1  "


def test_add_to_line_no_comments():
    # Covers line 22-23 (comments is None or empty)
    result = add_to_line(
        comments=None,
        original_string="x = 1",
        removed=False,
        comment_prefix="#",
    )
    assert result == "x = 1"

    result_empty = add_to_line(
        comments=[],
        original_string="x = 1",
        removed=False,
        comment_prefix="#",
    )
    assert result_empty == "x = 1"


def test_add_to_line_with_unique_and_duplicate_comments():
    # Covers lines 25-29 (filtering unique comments and formatting output)
    result = add_to_line(
        comments=["comment1", "comment2", "comment1"],
        original_string="x = 1",
        removed=False,
        comment_prefix="#",
    )
    assert result == "x = 1# comment1; comment2"
