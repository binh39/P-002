# file: src\sample_repo\isort\isort\comments.py:12-29
# asked: {"lines": [12, 13, 14, 15, 16, 17, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}
# gained: {"lines": [12, 13, 14, 15, 16, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}

from isort.comments import add_to_line


def test_add_to_line_removed():
    # Covers line 19-20 (removed=True)
    result = add_to_line(comments=["# comment"], original_string="import os  # comment", removed=True)
    assert result == "import os  "


def test_add_to_line_no_comments():
    # Covers line 22-23 (comments is None or empty)
    assert add_to_line(None, "import os") == "import os"
    assert add_to_line([], "import os") == "import os"


def test_add_to_line_with_unique_and_duplicates():
    # Covers lines 25-29 (unique_comments filtering and joining)
    comments = ["# first", "# second", "# first"]
    result = add_to_line(
        comments=comments,
        original_string="import sys",
        comment_prefix="#",
    )
    assert result == "import sys# # first; # second"
