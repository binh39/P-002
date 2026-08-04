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
        "include_trailing_comma": False,
        "white_space": " ",
    }
    assert hanging_indent(**interface) == ""


def test_hanging_indent_first_import_exceeds_limit():
    interface = {
        "imports": ["very_long_import_name_that_exceeds_limit"],
        "statement": "import ",
        "line_length": 10,  # line_length_limit = 7
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "include_trailing_comma": False,
        "white_space": " ",
    }
    result = hanging_indent(**interface)
    assert "very_long_import_name_that_exceeds_limit" in result


def test_hanging_indent_multiple_imports_and_wrapping():
    # Test multiple imports where one of them triggers wrapping in the while loop
    interface = {
        "imports": ["a", "b" * 30],
        "statement": "import ",
        "line_length": 20,  # limit 17
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "include_trailing_comma": False,
        "white_space": " ",
    }
    result = hanging_indent(**interface)
    assert "\n" in result


def test_hanging_indent_with_comments_fitting():
    interface = {
        "imports": ["a"],
        "statement": "import a",
        "line_length": 80,  # limit 77
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": "#",
        "include_trailing_comma": False,
        "white_space": " ",
    }
    result = hanging_indent(**interface)
    assert "# comment" in result


def test_hanging_indent_with_comments_exceeding_fitting():
    interface = {
        "imports": ["a"],
        "statement": "import a",
        "line_length": 15,  # limit 12, statement_with_comments will exceed 12 + 2 = 14
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# a very long comment here"],
        "remove_comments": False,
        "comment_prefix": "#",
        "include_trailing_comma": False,
        "white_space": " ",
    }
    result = hanging_indent(**interface)
    assert "\n" in result
    assert "# a very long comment here" in result
