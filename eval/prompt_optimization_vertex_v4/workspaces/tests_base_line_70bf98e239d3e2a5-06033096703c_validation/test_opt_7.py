# file: src\sample_repo\isort\isort\comments.py:12-29
# asked: {"lines": [12, 13, 14, 15, 16, 17, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}
# gained: {"lines": [12, 13, 14, 15, 16, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}

from isort.comments import add_to_line


def test_add_to_line_removed():
    # Tests line 19-20: removed is True
    result = add_to_line(comments=["# comment"], original_string="import os # comment", removed=True)
    assert result == "import os "


def test_add_to_line_no_comments():
    # Tests line 22-23: comments is None or empty
    result1 = add_to_line(comments=None, original_string="import os")
    assert result1 == "import os"

    result2 = add_to_line(comments=[], original_string="import os")
    assert result2 == "import os"


def test_add_to_line_with_unique_and_duplicate_comments():
    # Tests lines 25-29: adding unique comments and handling duplicates
    comments = ["# first", "# second", "# first"]
    result = add_to_line(comments=comments, original_string="import os", comment_prefix="#")
    assert result == "import os# # first; # second"
