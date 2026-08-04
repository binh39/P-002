# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}

import pytest
from isort.wrap_modes import hanging_indent

def test_hanging_indent_empty_imports():
    interface = {
        "imports": [],
        "statement": "import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": " #",
    }
    assert hanging_indent(**interface) == ""

def test_hanging_indent_first_import_overflow():
    interface = {
        "imports": ["very_long_import_name_that_exceeds_limit"],
        "statement": "from module import ",
        "line_length": 20,  # line_length_limit = 17
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": " #",
    }
    # First statement length is len("from module import very_long_...") > 17
    res = hanging_indent(**interface)
    assert "\n    very_long_import_name_that_exceeds_limit" in res

def test_hanging_indent_multiple_imports_and_overflow_and_comments():
    # Test multiple imports where one causes inner while loop line overflow,
    # and comments branch where statement_with_comments exceeds length limit
    # leading to the comment being wrapped to the indent line.
    interface = {
        "imports": ["import_a", "import_b_which_is_super_long"],
        "statement": "from mod import ",
        "line_length": 25,  # line_length_limit = 22
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["comment"],
        "remove_comments": False,
        "comment_prefix": " #",
    }
    res = hanging_indent(**interface)
    assert isinstance(res, str)
    assert "import_a" in res
    assert "import_b_which_is_super_long" in res

def test_hanging_indent_comments_fits_on_line():
    # Comments present, but statement_with_comments fits within line_length_limit + 2
    interface = {
        "imports": ["a"],
        "statement": "import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["comment"],
        "remove_comments": False,
        "comment_prefix": " #",
    }
    res = hanging_indent(**interface)
    assert res == "import a # comment"

def test_hanging_indent_no_comments_returns_statement():
    # No comments, hits final return str(interface["statement"])
    interface = {
        "imports": ["a", "b"],
        "statement": "import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": " #",
    }
    res = hanging_indent(**interface)
    assert res == "import a, b"
