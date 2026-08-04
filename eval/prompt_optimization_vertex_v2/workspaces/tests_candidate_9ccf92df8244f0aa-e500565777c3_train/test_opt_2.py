# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 157]]}

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
        "include_trailing_comma": False,
        "white_space": " ",
    }
    assert hanging_indent(**interface) == ""


def test_hanging_indent_first_import_exceeds_limit():
    interface = {
        "imports": ["very_long_import_name_that_exceeds_limit"],
        "statement": "import ",
        "line_length": 15,  # line_length_limit = 12
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "include_trailing_comma": False,
        "white_space": " ",
    }
    result = hanging_indent(**interface)
    assert "\n    very_long_import_name_that_exceeds_limit" in result


def test_hanging_indent_multiple_imports_with_wrap_and_comments_short():
    interface = {
        "imports": ["a", "b", "c"],
        "statement": "import ",
        "line_length": 10,  # line_length_limit = 7
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": "#",
        "include_trailing_comma": False,
        "white_space": " ",
    }
    result = hanging_indent(**interface)
    # Should fit statement_with_comments length <= line_length_limit + 2 (9)
    assert "# comment" in result


def test_hanging_indent_multiple_imports_with_wrap_and_comments_long():
    interface = {
        "imports": ["a", "b", "c"],
        "statement": "import ",
        "line_length": 5,  # line_length_limit = 2
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# a very long comment that forces the comment wrapping branch"],
        "remove_comments": False,
        "comment_prefix": "#",
        "include_trailing_comma": False,
        "white_space": " ",
    }
    result = hanging_indent(**interface)
    # Should hit lines 157-164 (comment on indented new line)
    assert "\n    " in result
    assert "comment" in result


def test_hanging_indent_no_comments_returns_statement():
    interface = {
        "imports": ["a", "b"],
        "statement": "import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "include_trailing_comma": False,
        "white_space": " ",
    }
    result = hanging_indent(**interface)
    assert result == "import a, b"
