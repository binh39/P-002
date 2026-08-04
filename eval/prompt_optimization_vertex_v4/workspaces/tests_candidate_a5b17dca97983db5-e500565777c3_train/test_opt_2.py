# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [146, 147], [153, 156], [153, 157]]}

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
    # Test first import wrapping and multiple imports wrapping with comments
    interface = {
        "imports": ["a", "b_very_long_import_name_to_trigger_wrapping", "c"],
        "statement": "from module import ",
        "line_length": 20,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": " # ",
    }
    result = hanging_indent(**interface)
    assert isinstance(result, str)
    assert "a" in result


def test_hanging_indent_comment_wrapping_branches():
    # Test when statement_with_comments exceeds line length limit (triggers line 157)
    interface_exceeds = {
        "imports": ["foo"],
        "statement": "import ",
        "line_length": 15,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# a comment that is quite long"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result_exceeds = hanging_indent(**interface_exceeds)
    assert "\n" in result_exceeds

    # Test when statement_with_comments fits within line length limit (triggers line 156)
    interface_fits = {
        "imports": ["foo"],
        "statement": "import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# c"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result_fits = hanging_indent(**interface_fits)
    assert "#" in result_fits
