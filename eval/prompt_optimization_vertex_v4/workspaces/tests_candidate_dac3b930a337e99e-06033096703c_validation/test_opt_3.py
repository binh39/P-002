# file: src\sample_repo\isort\isort\comments.py:12-29
# asked: {"lines": [12, 13, 14, 15, 16, 17, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}
# gained: {"lines": [12, 13, 14, 15, 16, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}

from isort.comments import add_to_line


def test_add_to_line_removed():
    # Covers line 19-20 (removed=True)
    result = add_to_line(comments=["# comment"], original_string="x = 1  # comment", removed=True)
    assert result == "x = 1  "


def test_add_to_line_no_comments():
    # Covers line 22-23 (comments is None or empty)
    assert add_to_line(None, original_string="x = 1") == "x = 1"
    assert add_to_line([], original_string="x = 1") == "x = 1"


def test_add_to_line_unique_comments_and_formatting():
    # Covers lines 25-29 (unique comment filtering and joining)
    comments = ["comment1", "comment2", "comment1"]
    result = add_to_line(
        comments=comments,
        original_string="x = 1",
        removed=False,
        comment_prefix="#",
    )
    assert result == "x = 1# comment1; comment2"
