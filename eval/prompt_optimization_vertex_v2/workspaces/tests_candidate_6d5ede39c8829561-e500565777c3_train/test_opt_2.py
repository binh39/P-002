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
        "comment_prefix": " #",
    }
    assert hanging_indent(**interface) == ""

def test_hanging_indent_first_import_exceeds_limit():
    # line_length = 10, line_length_limit = 7
    # statement = "from a import " (14 chars > 7)
    interface = {
        "imports": ["b"],
        "statement": "from a import ",
        "line_length": 10,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": " #",
    }
    result = hanging_indent(**interface)
    # Should wrap first import onto a new line
    assert "\n    b" in result

def test_hanging_indent_multiple_imports_and_wrap():
    # Test while loop with multiple imports, where one import triggers a wrap
    interface = {
        "imports": ["b", "c_very_long_import_name"],
        "statement": "import ",
        "line_length": 15, # limit = 12
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": " #",
    }
    result = hanging_indent(**interface)
    assert "c_very_long_import_name" in result

def test_hanging_indent_comments_fitting_on_line():
    interface = {
        "imports": ["b"],
        "statement": "import a, ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["comment"],
        "remove_comments": False,
        "comment_prefix": " #",
    }
    result = hanging_indent(**interface)
    assert "# comment" in result

def test_hanging_indent_comments_exceeding_line():
    # Make comment not fit on the last line, triggering the second return in comment block
    interface = {
        "imports": ["b"],
        "statement": "import a",
        "line_length": 12, # limit = 9
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["very_long_comment_string"],
        "remove_comments": False,
        "comment_prefix": " #",
    }
    result = hanging_indent(**interface)
    assert "very_long_comment_string" in result

def test_hanging_indent_no_comments_returns_statement():
    interface = {
        "imports": ["b"],
        "statement": "import a",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": " #",
    }
    result = hanging_indent(**interface)
    assert result == "import ab"
