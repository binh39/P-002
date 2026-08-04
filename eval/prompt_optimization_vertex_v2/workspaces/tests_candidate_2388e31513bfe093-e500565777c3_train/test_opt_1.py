# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}

import pytest
from isort.wrap_modes import hanging_indent


def test_hanging_indent_empty_imports():
    """Test hanging_indent when imports list is empty."""
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
    result = hanging_indent(**interface)
    assert result == ""


def test_hanging_indent_first_import_fits():
    """Test hanging_indent where the first import fits within the line length limit."""
    interface = {
        "imports": ["os"],
        "statement": "import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert result == "import os"


def test_hanging_indent_first_import_exceeds_limit():
    """Test hanging_indent where the first import exceeds line length limit."""
    interface = {
        "imports": ["very_long_module_name_that_exceeds_the_line_length_limit"],
        "statement": "from a.b.c.d.e.f.g import ",
        "line_length": 30,  # line_length_limit = 27
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    # line_length_limit = 27
    # statement="from a.b.c.d.e.f.g import " -> len is 26 <= 27, but next_statement = statement + next_import is > 27
    assert "\n" in result
    assert "very_long_module_name_that_exceeds_the_line_length_limit" in result


def test_hanging_indent_multiple_imports_no_wrap_then_wrap():
    """Test multiple imports where one does not wrap and subsequent wraps."""
    interface = {
        "imports": ["sys", "os", "very_long_module_name_to_force_wrapping_in_while_loop"],
        "statement": "import ",
        "line_length": 40,  # line_length_limit = 37
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "sys" in result
    assert "os" in result
    assert "very_long_module_name_to_force_wrapping_in_while_loop" in result
    assert "\n" in result


def test_hanging_indent_with_comments_fits_line():
    """Test hanging_indent with comments that fit on the final line."""
    interface = {
        "imports": ["os"],
        "statement": "import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "os" in result
    assert "# comment" in result


def test_hanging_indent_with_comments_exceeds_line_drops_to_indent():
    """Test hanging_indent with comments that exceed the final line length limit, dropping comment to indented line."""
    interface = {
        "imports": ["os"],
        "statement": "import ",
        "line_length": 15,  # line_length_limit = 12, limit+2 = 14
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# very long comment that overflows"],
        "remove_comments": False,
        "comment_prefix": "# ",
    }
    result = hanging_indent(**interface)
    assert "os" in result
    assert "\n" in result
    assert "# very long comment that overflows" in result
