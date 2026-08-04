# file: src\sample_repo\isort\isort\comments.py:12-29
# asked: {"lines": [12, 13, 14, 15, 16, 17, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}
# gained: {"lines": [12, 13, 14, 15, 16, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}

from isort.comments import add_to_line


def test_add_to_line_removed() -> None:
    # Covers line 19-20: if removed: return parse(original_string)[0]
    result = add_to_line(comments=["# comment"], original_string="x = 1  # comment", removed=True)
    assert result == "x = 1  "


def test_add_to_line_no_comments() -> None:
    # Covers line 22-23: if not comments: return original_string
    result_none = add_to_line(comments=None, original_string="x = 1")
    assert result_none == "x = 1"

    result_empty = add_to_line(comments=[], original_string="x = 1")
    assert result_empty == "x = 1"


def test_add_to_line_unique_comments_and_prefix() -> None:
    # Covers lines 25-29: deduplication and formatting with comment_prefix
    comments = ["# comment1", "# comment2", "# comment1"]
    result = add_to_line(
        comments=comments,
        original_string="x = 1",
        removed=False,
        comment_prefix="  #",
    )
    assert result == "x = 1  # # comment1; # comment2"
