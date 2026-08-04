# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}

import pytest
from isort.wrap_modes import hanging_indent


def test_hanging_indent_empty_imports():
    """Test hanging_indent when imports list is empty (line 119-120)."""
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
    result = hanging_indent(**interface)
    assert result == ""


def test_hanging_indent_first_import_exceeds_limit():
    """Test hanging_indent when the first import exceeds line length limit (line 127-132)."""
    interface = {
        "imports": ["very_long_import_name_that_exceeds_limit"],
        "statement": "from module import ",
        "line_length": 20,  # line_length_limit = 17
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    # line_length_limit = 17. statement + next_import has length > 17
    assert "very_long_import_name_that_exceeds_limit" in result
    assert "\n    " in result


def test_hanging_indent_multiple_imports_with_wrap():
    """Test hanging_indent with multiple imports where a later line exceeds limit (line 136-144)."""
    interface = {
        "imports": ["short", "another_very_long_import_that_forces_wrap"],
        "statement": "from module import ",
        "line_length": 30,  # line_length_limit = 27
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "short" in result
    assert "another_very_long_import_that_forces_wrap" in result
    assert "\n    " in result


def test_hanging_indent_with_comments_fits():
    """Test hanging_indent with comments that fit within the line limit (line 146-156)."""
    interface = {
        "imports": ["a"],
        "statement": "from module import a",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "# comment" in result


def test_hanging_indent_with_comments_exceeds_limit():
    """Test hanging_indent with comments that exceed the line limit, forcing comment wrapping (line 157-164)."""
    interface = {
        "imports": ["a"],
        "statement": "from module import a",
        "line_length": 25,  # line_length_limit = 22
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# very long comment that causes overflow"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "\n" in result
    assert "very long comment" in result


def test_hanging_indent_no_comments_returns_statement():
    """Test hanging_indent with no comments returns statement directly (line 167)."""
    interface = {
        "imports": ["a", "b"],
        "statement": "from module import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert result == "from module import a, b"
