# file: src\sample_repo\isort\isort\wrap_modes.py:311-364
# asked: {"lines": [311, 312, 313, 314, 316, 318, 319, 320, 322, 323, 324, 325, 326, 327, 328, 330, 332, 333, 334, 335, 337, 338, 340, 341, 342, 345, 346, 347, 348, 349, 351, 352, 353, 354, 355, 356, 357, 358, 360, 362, 363, 364], "branches": [[313, 314], [313, 316], [322, 323], [322, 333], [334, 335], [334, 364], [336, 340], [336, 345], [352, 353], [352, 363]]}
# gained: {"lines": [311, 312, 313, 314, 316, 318, 319, 320, 322, 323, 324, 325, 326, 327, 328, 330, 332, 333, 334, 335, 337, 338, 340, 341, 342, 345, 346, 347, 348, 349, 351, 352, 363, 364], "branches": [[313, 314], [313, 316], [322, 323], [322, 333], [334, 335], [334, 364], [336, 340], [336, 345], [352, 363]]}

import pytest
from isort.wrap_modes import hanging_indent_with_parentheses

def test_hanging_indent_with_parentheses_empty():
    interface = {
        "imports": [],
        "line_length": 80,
        "statement": "from module import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "indent": "    ",
        "include_trailing_comma": False,
    }
    assert hanging_indent_with_parentheses(**interface) == ""

def test_hanging_indent_with_parentheses_first_import_exceeds_limit():
    interface = {
        "imports": ["a", "b"],
        "line_length": 15,
        "statement": "from mod import ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "indent": "    ",
        "include_trailing_comma": True,
    }
    # "from mod import (" len is 16 > line_length_limit (14)
    res = hanging_indent_with_parentheses(**interface)
    assert "a" in res
    assert "b" in res

def test_hanging_indent_with_parentheses_hash_in_statement():
    interface = {
        "imports": ["b", "c"],
        "line_length": 40,
        "statement": "from mod import a # comment",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "indent": "    ",
        "include_trailing_comma": False,
    }
    res = hanging_indent_with_parentheses(**interface)
    assert "b" in res
    assert "c" in res

def test_hanging_indent_with_parentheses_current_line_exceeds_limit():
    interface = {
        "imports": ["very_long_import_name_here"],
        "line_length": 20,
        "statement": "from mod import ",
        "comments": ["# comm"],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "indent": "    ",
        "include_trailing_comma": True,
    }
    res = hanging_indent_with_parentheses(**interface)
    assert "very_long_import_name_here" in res
