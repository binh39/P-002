# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}

import pytest
from isort.wrap_modes import hanging_indent


def test_hanging_indent_empty_imports():
    """Test hanging_indent when imports list is empty (lines 119-120)."""
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


def test_hanging_indent_basic_and_loops():
    """Test hanging_indent with various wrapping scenarios covering lines 124-167."""
    # Scenario 1: First import exceeds line length limit (triggers line 127/128)
    # Plus multiple imports where one exceeds the limit in the while loop (triggers line 139)
    # Plus comments where statement_with_comments exceeds line_length_limit + 2 (triggers lines 157-164)
    interface = {
        "imports": ["very_long_import_name_that_forces_wrap_1", "another_long_import_name_to_force_wrap_2"],
        "statement": "from module import ",
        "line_length": 40,  # line_length_limit = 37
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": " #",
    }
    
    res = hanging_indent(**interface)
    assert isinstance(res, str)
    assert len(res) > 0


def test_hanging_indent_short_comments():
    """Test hanging_indent where comments fit on the line (triggers line 156)."""
    interface = {
        "imports": ["a"],
        "statement": "import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": " #",
    }
    res = hanging_indent(**interface)
    assert "import a" in res
    assert "# comment" in res


def test_hanging_indent_no_comments_simple():
    """Test hanging_indent with no comments (triggers line 167 return statement)."""
    interface = {
        "imports": ["a", "b"],
        "statement": "import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    res = hanging_indent(**interface)
    assert res == "import a, b"
