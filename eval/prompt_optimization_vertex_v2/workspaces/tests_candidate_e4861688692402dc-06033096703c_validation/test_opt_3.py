# file: src\sample_repo\isort\isort\comments.py:12-29
# asked: {"lines": [12, 13, 14, 15, 16, 17, 19, 20, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 20], [19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}
# gained: {"lines": [12, 13, 14, 15, 16, 19, 22, 23, 25, 26, 27, 28, 29], "branches": [[19, 22], [22, 23], [22, 25], [26, 27], [26, 29], [27, 26], [27, 28]]}

import pytest
from isort.comments import add_to_line




def test_add_to_line_no_comments() -> None:
    # Covers line 22-23 (comments is None or empty)
    assert add_to_line(None, original_string="import os") == "import os"
    assert add_to_line([], original_string="import os") == "import os"


def test_add_to_line_with_unique_and_duplicate_comments() -> None:
    # Covers lines 25-29 (adding unique comments, de-duplicating, and formatting with prefix)
    result = add_to_line(
        comments=["# c1", "# c2", "# c1"],
        original_string="import os",
        removed=False,
        comment_prefix="  #",
    )
    assert result == "import os  # # c1; # c2"
