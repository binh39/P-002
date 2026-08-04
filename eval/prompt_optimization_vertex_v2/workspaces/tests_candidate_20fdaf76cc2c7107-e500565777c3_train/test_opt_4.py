# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [146, 147], [146, 167], [153, 156], [153, 157]]}

import pytest
from isort.wrap_modes import hanging_indent


def test_hanging_indent_no_imports():
    interface = {
        "imports": [],
        "statement": "import something",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    assert hanging_indent(**interface) == ""


def test_hanging_indent_first_import_short():
    # line_length_limit = 80 - 3 = 77
    interface = {
        "imports": ["foo"],
        "statement": "from module import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # len("from module import foo") <= 77 -> no wrap on first import
    result = hanging_indent(**interface)
    assert result == "from module import foo"


def test_hanging_indent_first_import_long():
    # line_length_limit = 15 - 3 = 12
    # statement + import length > 12 -> triggers first import wrap
    interface = {
        "imports": ["verylongimportname"],
        "statement": "from mod import ",
        "line_length": 15,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "verylongimportname" in result
    assert "\n    verylongimportname" in result


def test_hanging_indent_multiple_imports_short_and_long_lines():
    # Test multiple imports where one fits and another exceeds the line length limit on the last line.
    interface = {
        "imports": ["foo", "verylongimportnamethatexceedslimit"],
        "statement": "from mod import ",
        "line_length": 25,  # line_length_limit = 22
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "foo" in result
    assert "verylongimportnamethatexceedslimit" in result


def test_hanging_indent_with_comments_short_line():
    interface = {
        "imports": ["foo"],
        "statement": "import ",
        "line_length": 80,  # limit = 77
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "foo" in result
    assert "# comment" in result


def test_hanging_indent_with_comments_long_line():
    interface = {
        "imports": ["foo"],
        "statement": "import ",
        "line_length": 15,  # limit = 12
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": " #",
    }
    result = hanging_indent(**interface)
    assert "foo" in result
    assert "# comment" in result
