# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [146, 147], [146, 167], [153, 156], [153, 157]]}

import pytest
from isort.wrap_modes import hanging_indent

def test_hanging_indent_empty_imports():
    interface = {
        "imports": [],
        "statement": "from module import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    assert hanging_indent(**interface) == ""

def test_hanging_indent_basic_and_wrapping():
    # Test line 127 branch (first import too long) and while loop (lines 136-144) with normal and wrapping conditions
    interface = {
        "imports": ["very_long_import_name_one", "short"],
        "statement": "from module import ",
        "line_length": 30,  # line_length_limit = 27
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # "from module import very_long_import_name_one" len is > 27, so triggers line 127
    # Then second import "short" added with ", ", and maybe wraps or doesn't depending on length
    res = hanging_indent(**interface)
    assert "very_long_import_name_one" in res

def test_hanging_indent_multiple_imports_wrapping():
    # Ensure inner while loop wraps when statement split line exceeds limit
    interface = {
        "imports": ["import1", "import_two_that_is_long"],
        "statement": "from m import ",
        "line_length": 25,  # limit = 22
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    res = hanging_indent(**interface)
    assert "\n" in res

def test_hanging_indent_with_comments_fitting():
    interface = {
        "imports": ["a"],
        "statement": "from m import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["comment"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    res = hanging_indent(**interface)
    assert "# comment" in res

def test_hanging_indent_with_comments_exceeding_limit():
    # Triggers the branch where statement_with_comments exceeds line_length_limit + 2 (lines 157-164)
    interface = {
        "imports": ["a"],
        "statement": "from m import ",
        "line_length": 20,  # limit = 17, limit+2 = 19
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["a_very_long_comment_that_forces_wrap"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    res = hanging_indent(**interface)
    assert "\n" in res
    assert "a_very_long_comment_that_forces_wrap" in res
