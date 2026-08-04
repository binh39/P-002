# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}

import pytest
from isort.wrap_modes import hanging_indent

def test_hanging_indent_empty_imports():
    interface = {
        "imports": [],
        "statement": "import a",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    assert hanging_indent(**interface) == ""

def test_hanging_indent_first_import_overflow():
    interface = {
        "imports": ["b"],
        "statement": "import a, ",
        "line_length": 10,  # limit = 7
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # next_statement length > 7 triggers line 127
    result = hanging_indent(**interface)
    assert "import a," in result
    assert "b" in result

def test_hanging_indent_multiple_imports_and_overflow():
    interface = {
        "imports": ["b", "c"],
        "statement": "import a",
        "line_length": 15,  # limit = 12
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # This will exercise the while loop (lines 136-144) and internal overflow check (line 139)
    result = hanging_indent(**interface)
    assert "a" in result
    assert "b" in result
    assert "c" in result

def test_hanging_indent_with_comments_fits():
    interface = {
        "imports": ["b"],
        "statement": "import a",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["comment"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # Should fit and return statement_with_comments directly (line 156)
    result = hanging_indent(**interface)
    assert "#" in result

def test_hanging_indent_with_comments_overflow():
    interface = {
        "imports": ["b"],
        "statement": "import a",
        "line_length": 10,  # limit = 7
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["very_long_comment_here"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # Should exceed line_length_limit + 2 and trigger lines 157-164
    result = hanging_indent(**interface)
    assert "very_long_comment_here" in result
    assert "\n" in result
