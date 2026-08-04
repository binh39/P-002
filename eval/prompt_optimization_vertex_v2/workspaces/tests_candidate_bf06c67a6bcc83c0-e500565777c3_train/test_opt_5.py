# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 144, 146, 147, 148, 149, 150, 151, 153, 154, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 144], [146, 147], [146, 167], [153, 157]]}

import pytest
from isort.wrap_modes import hanging_indent


def test_hanging_indent_empty_imports():
    interface = {
        "imports": [],
        "statement": "import os",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    assert hanging_indent(**interface) == ""


def test_hanging_indent_first_import_exceeds_limit():
    interface = {
        "imports": ["sys"],
        "statement": "import ",
        "line_length": 8,  # limit = 5
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # len("import sys") = 10 > 5 -> triggers line 127
    result = hanging_indent(**interface)
    assert "sys" in result


def test_hanging_indent_multiple_imports_and_line_wrap():
    interface = {
        "imports": ["a", "b", "c"],
        "statement": "from mod import ",
        "line_length": 15,  # limit = 12
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # Should exercise the while loop and line 139 (len of last line > line_length_limit)
    result = hanging_indent(**interface)
    assert "a" in result
    assert "b" in result
    assert "c" in result




def test_hanging_indent_with_comments_exceeds_limit():
    interface = {
        "imports": ["os"],
        "statement": "import ",
        "line_length": 15,  # limit = 12
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["very_long_comment_here"],
        "remove_comments": False,
        "comment_prefix": "# ",
    }
    # Comments exceed last line limit, triggering lines 157-164
    result = hanging_indent(**interface)
    assert "very_long_comment_here" in result


def test_hanging_indent_no_comments_returns_statement():
    interface = {
        "imports": ["os"],
        "statement": "import ",
        "line_length": 80,  # limit = 77
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # Triggers line 167 (no comments, returns statement)
    result = hanging_indent(**interface)
    assert result == "import os"
