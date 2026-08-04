# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [153, 156], [153, 157]]}

from typing import Any
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

def test_hanging_indent_basic_and_long_first_import_and_while_loop():
    # Test first import exceeding limit, subsequent imports with wrap, comments fitting, comments not fitting
    # line_length = 15 -> line_length_limit = 12
    # First import makes statement too long
    interface = {
        "imports": ["a", "b", "c"],
        "statement": "from mod import ",
        "line_length": 15,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    
    # Let's trace:
    # interface["statement"] = "from mod import " (len 16)
    # line_length_limit = 15 - 3 = 12
    # next_import = "a"
    # next_statement = "from mod import a" (len 17 > 12) -> triggers line 127
    # next_statement becomes: _hanging_indent_end_line("from mod import ") + "\n" + "    " + "a"
    
    res = hanging_indent(**interface)
    assert isinstance(res, str)
    assert res != ""

def test_hanging_indent_while_loop_wrap_and_comments_overflow():
    # Force while loop to trigger line 139 (len(next_statement.split(...) ) > line_length_limit)
    # and comments overflow (lines 157-164)
    interface = {
        "imports": ["verylongimport1", "verylongimport2"],
        "statement": "import ",
        "line_length": 15,  # line_length_limit = 12
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# verylongcommentthatoverflows"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    res = hanging_indent(**interface)
    assert isinstance(res, str)
    assert "\n" in res

def test_hanging_indent_comments_fitting():
    # Comments fit within line_length_limit + 2 (line 153-156)
    interface = {
        "imports": ["a"],
        "statement": "import ",
        "line_length": 80,  # limit 77
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# c"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    res = hanging_indent(**interface)
    assert "# c" in res
