# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [146, 147], [146, 167], [153, 156], [153, 157]]}

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


def test_hanging_indent_first_import_long_and_multiple_imports():
    # line_length = 10 -> line_length_limit = 7
    # statement = "from x import " (len = 14 > 7 -> triggers first import wrap)
    # imports = ["longimport1", "longimport2"] -> triggers while loop and second import wrap
    interface = {
        "imports": ["longimport1", "longimport2"],
        "statement": "from x import ",
        "line_length": 10,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "longimport1" in result
    assert "longimport2" in result


def test_hanging_indent_with_comments_short_enough():
    interface = {
        "imports": ["b"],
        "statement": "import a",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": "# ",
    }
    result = hanging_indent(**interface)
    assert "# comment" in result


def test_hanging_indent_with_comments_too_long():
    interface = {
        "imports": ["b"],
        "statement": "import a",
        "line_length": 5,  # line_length_limit = 2
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["comment"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "\n" in result
    assert "comment" in result


def test_hanging_indent_no_comments_normal_return():
    interface = {
        "imports": ["b"],
        "statement": "import a",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert result == "import ab"
