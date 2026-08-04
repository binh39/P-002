# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [146, 147], [146, 167], [153, 156]]}

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

def test_hanging_indent_basic_and_wrapping():
    # Test first import exceeding line length and multiple imports with loop wrapping
    interface = {
        "imports": ["very_long_import_name_one", "very_long_import_name_two"],
        "statement": "from module import ",
        "line_length": 30,  # line_length_limit = 27
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "very_long_import_name_one" in result
    assert "very_long_import_name_two" in result

def test_hanging_indent_with_comments_fitting():
    interface = {
        "imports": ["foo"],
        "statement": "import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["comment"],
        "remove_comments": False,
        "comment_prefix": "# ",
    }
    result = hanging_indent(**interface)
    assert "foo" in result
    assert "comment" in result

def test_hanging_indent_with_comments_exceeding():
    interface = {
        "imports": ["foo"],
        "statement": "import " + "x" * 70,
        "line_length": 80,  # line_length_limit = 77
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["comment"],
        "remove_comments": False,
        "comment_prefix": "# ",
    }
    result = hanging_indent(**interface)
    assert "comment" in result
    assert "\n" in result
