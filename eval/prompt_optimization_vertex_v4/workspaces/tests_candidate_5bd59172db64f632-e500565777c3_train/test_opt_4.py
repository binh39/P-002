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


def test_hanging_indent_first_import_exceeds_limit():
    interface = {
        "imports": ["very_long_import_name_here"],
        "statement": "from module import ",
        "line_length": 25,  # limit = 22
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # next_statement = "from module import very_long_import_name_here" (length > 22)
    # Triggers line 127/128 (first import exceeds limit)
    result = hanging_indent(**interface)
    assert "very_long_import_name_here" in result


def test_hanging_indent_multiple_imports_and_wrapping():
    interface = {
        "imports": ["a", "b" * 30],
        "statement": "from module import ",
        "line_length": 40,  # limit = 37
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # First import 'a' fits. Second import 'b'*30 causes line 139 to trigger wrapping.
    result = hanging_indent(**interface)
    assert "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" in result


def test_hanging_indent_with_comments_fits():
    interface = {
        "imports": ["a"],
        "statement": "from module import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["comment"],
        "remove_comments": False,
        "comment_prefix": "# ",
    }
    # Comments fit within line length limit + 2
    result = hanging_indent(**interface)
    assert "comment" in result


def test_hanging_indent_with_comments_exceeds():
    interface = {
        "imports": ["a" * 70],
        "statement": "from module import ",
        "line_length": 40,  # limit = 37, comment check limit = 39
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["very_long_comment_that_forces_wrap"],
        "remove_comments": False,
        "comment_prefix": "# ",
    }
    # statement_with_comments length > line_length_limit + 2, triggering lines 157-164
    result = hanging_indent(**interface)
    assert "very_long_comment_that_forces_wrap" in result
