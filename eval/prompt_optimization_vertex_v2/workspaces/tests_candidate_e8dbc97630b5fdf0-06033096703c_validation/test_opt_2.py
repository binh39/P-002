# file: src\sample_repo\isort\isort\comments.py:12-29
# asked: {"lines": [12, 13, 14, 15, 16, 17, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}
# gained: {"lines": [12, 13, 14, 15, 16, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}

from isort.comments import add_to_line


def test_add_to_line_removed() -> None:
    # Covers line 19-20: if removed
    result = add_to_line(comments=["# comment"], original_string="x = 1  # comment", removed=True)
    # parse("x = 1  # comment")[0] returns "x = 1  " because line.find('#') finds the comment
    # and slices line[:comment_start] which retains trailing spaces before the '#'.
    assert result == "x = 1  "


def test_add_to_line_no_comments() -> None:
    # Covers line 22-23: if not comments (None or empty list)
    assert add_to_line(None, "x = 1") == "x = 1"
    assert add_to_line([], "x = 1") == "x = 1"


def test_add_to_line_with_unique_and_duplicate_comments() -> None:
    # Covers lines 25-29: unique comments filtering and formatting output
    comments = ["# a", "# b", "# a"]
    result = add_to_line(
        comments=comments,
        original_string="x = 1",
        removed=False,
        comment_prefix="  #",
    )
    assert result == "x = 1  # # a; # b"
