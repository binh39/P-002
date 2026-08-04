# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}

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


def test_hanging_indent_basic():
    interface = {
        "imports": ["b", "c"],
        "statement": "from module import ",
        "line_length": 30,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # line_length_limit = 27
    # "from module import b" length is 19 <= 27
    # next import "c" -> "from module import b, c" length 23 <= 27
    result = hanging_indent(**interface)
    assert result == "from module import b, c"


def test_hanging_indent_first_statement_too_long():
    interface = {
        "imports": ["very_long_import_name"],
        "statement": "from module import ",
        "line_length": 25,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # line_length_limit = 22
    # len("from module import very_long_import_name") = 39 > 22
    # Triggers line 127/128 branch
    result = hanging_indent(**interface)
    assert "\\" in result


def test_hanging_indent_loop_item_too_long():
    interface = {
        "imports": ["b", "very_long_import_name_to_trigger_wrap"],
        "statement": "from module import ",
        "line_length": 30,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # First import 'b' fits. Second import makes line too long, triggering line 139 branch.
    result = hanging_indent(**interface)
    assert "\\" in result


def test_hanging_indent_comments_fits():
    interface = {
        "imports": ["b"],
        "statement": "import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["comment"],
        "remove_comments": False,
        "comment_prefix": " #",
    }
    result = hanging_indent(**interface)
    assert "comment" in result


def test_hanging_indent_comments_overflow():
    interface = {
        "imports": ["b"],
        "statement": "import a, ",
        "line_length": 15,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["a very long comment that will definitely exceed line length limit"],
        "remove_comments": False,
        "comment_prefix": " #",
    }
    # Triggers lines 157-164 where comments don't fit on the last line and are wrapped/moved.
    result = hanging_indent(**interface)
    assert "\n" in result
    assert "comment" in result
