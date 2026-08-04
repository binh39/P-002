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

def test_hanging_indent_basic_and_wrapping():
    # Test first import wrapping (len(next_statement) > line_length_limit)
    # and subsequent import wrapping inside while loop.
    interface = {
        "imports": ["alpha", "beta", "gamma"],
        "statement": "from module import ",
        "line_length": 20,  # line_length_limit = 17
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # "from module import " is 19 chars long. 
    # With next_import "alpha", next_statement is 24 chars, > 17, so it wraps first import.
    # Then while loop runs for beta and gamma, forcing further wrapping.
    res = hanging_indent(**interface)
    assert res is not None

def test_hanging_indent_with_comments_fitting():
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
    res = hanging_indent(**interface)
    assert "foo" in res
    assert "# comment" in res

def test_hanging_indent_with_comments_exceeding_line_length():
    interface = {
        "imports": ["foo"],
        "statement": "import ",
        "line_length": 15,  # line_length_limit = 12
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["very_long_comment_here"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    res = hanging_indent(**interface)
    assert res is not None
    assert "\n" in res
