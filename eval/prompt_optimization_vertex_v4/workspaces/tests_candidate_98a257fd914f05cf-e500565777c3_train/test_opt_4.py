# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [146, 147], [146, 167], [153, 156], [153, 157]]}

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
        "comment_prefix": "#",
    }
    assert hanging_indent(**interface) == ""


def test_hanging_indent_basic_and_while_loops():
    # Test first import too long (> line_length_limit)
    # Test subsequent imports, one normal, one triggering the line length check in while loop
    interface = {
        "imports": ["very_long_import_name_one", "short", "another_very_long_import_name_two"],
        "statement": "from module import ",
        "line_length": 20,  # limit = 17
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "very_long_import_name_one" in result
    assert "another_very_long_import_name_two" in result


def test_hanging_indent_with_comments_short_line():
    interface = {
        "imports": ["foo"],
        "statement": "import foo",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["comment"],
        "remove_comments": False,
        "comment_prefix": " #",
    }
    result = hanging_indent(**interface)
    assert "foo" in result
    assert "comment" in result


def test_hanging_indent_with_comments_long_line():
    interface = {
        "imports": ["foo"],
        "statement": "import foo",
        "line_length": 15,  # limit = 12
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["a_very_long_comment_that_forces_multiline_comment_handling"],
        "remove_comments": False,
        "comment_prefix": " #",
    }
    result = hanging_indent(**interface)
    assert "foo" in result
    assert "a_very_long_comment_that_forces_multiline_comment_handling" in result
