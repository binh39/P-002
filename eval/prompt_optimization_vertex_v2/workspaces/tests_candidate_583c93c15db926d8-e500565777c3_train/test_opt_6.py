# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [146, 147], [146, 167], [153, 156], [153, 157]]}

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
        "imports": ["very_long_import_name_that_triggers_wrap"],
        "statement": "from module import ",
        "line_length": 20,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    # line_length_limit = 20 - 3 = 17
    # "from module import very_long_import_name_that_triggers_wrap" length > 17
    # Should wrap first import onto a new line after indent
    assert "    very_long_import_name_that_triggers_wrap" in result


def test_hanging_indent_multiple_imports_and_wrap_loop():
    interface = {
        "imports": ["foo", "very_long_second_import_name_that_exceeds_line_limit"],
        "statement": "from module import ",
        "line_length": 30,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "foo" in result
    assert "very_long_second_import_name_that_exceeds_line_limit" in result


def test_hanging_indent_comments_fits_line():
    interface = {
        "imports": ["foo"],
        "statement": "import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["comment"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "#comment" in result or "# comment" in result


def test_hanging_indent_comments_exceeds_line_fits_on_indent_line():
    interface = {
        "imports": ["long_import_name_to_force_wrap_and_push_comments"],
        "statement": "import ",
        "line_length": 25,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["very_long_comment_that_forces_multiline_comment_handling"],
        "remove_comments": False,
        "comment_prefix": "# ",
    }
    result = hanging_indent(**interface)
    assert result is not None
