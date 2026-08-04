# file: src\sample_repo\isort\isort\comments.py:12-29
# asked: {"lines": [12, 13, 14, 15, 16, 17, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}
# gained: {"lines": [12, 13, 14, 15, 16, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}

import pytest
from isort.comments import add_to_line


def test_add_to_line_removed():
    # Covers line 19: if removed: return parse(original_string)[0]
    result = add_to_line(comments=["# comment"], original_string="import os # comment", removed=True)
    assert result == "import os "


def test_add_to_line_no_comments():
    # Covers line 22-23: if not comments: return original_string
    result = add_to_line(comments=None, original_string="import os")
    assert result == "import os"

    result_empty = add_to_line(comments=[], original_string="import os")
    assert result_empty == "import os"


def test_add_to_line_with_unique_comments():
    # Covers lines 25-29: uniqueness filtering and formatting with comment_prefix
    result = add_to_line(
        comments=["foo", "bar", "foo"],
        original_string="import os",
        removed=False,
        comment_prefix="  #",
    )
    assert result == "import os  # foo; bar"
