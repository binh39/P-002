# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}

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

def test_hanging_indent_first_import_exceeds_limit():
    interface = {
        "imports": ["very_long_import_name_that_exceeds_the_line_limit"],
        "statement": "from module import ",
        "line_length": 30,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    # line_length_limit = 30 - 3 = 27
    # "from module import " len = 19
    # next_import len = 47
    # next_statement len = 19 + 47 = 66 > 27 -> triggers first import wrapping branch
    assert "very_long_import_name_that_exceeds_the_line_limit" in result

def test_hanging_indent_multiple_imports_and_line_wrap():
    interface = {
        "imports": ["a", "b", "c"],
        "statement": "from mod import ",
        "line_length": 25,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "a" in result
    assert "b" in result
    assert "c" in result

def test_hanging_indent_with_comments_fitting():
    interface = {
        "imports": ["a"],
        "statement": "import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "import a" in result
    assert "# comment" in result

def test_hanging_indent_with_comments_exceeding():
    interface = {
        "imports": ["a"],
        "statement": "import ",
        "line_length": 15,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# a very long comment that forces comment wrapping"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "# a very long comment" in result
