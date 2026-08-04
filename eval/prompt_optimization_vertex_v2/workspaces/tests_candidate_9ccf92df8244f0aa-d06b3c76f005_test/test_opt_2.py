# file: src\sample_repo\isort\isort\wrap_modes.py:311-364
# asked: {"lines": [311, 312, 313, 314, 316, 318, 319, 320, 322, 323, 324, 325, 326, 327, 328, 330, 332, 333, 334, 335, 337, 338, 340, 341, 342, 345, 346, 347, 348, 349, 351, 352, 353, 354, 355, 356, 357, 358, 360, 362, 363, 364], "branches": [[313, 314], [313, 316], [322, 323], [322, 333], [334, 335], [334, 364], [336, 340], [336, 345], [352, 353], [352, 363]]}
# gained: {"lines": [311, 312, 313, 314, 316, 318, 319, 320, 322, 323, 324, 325, 326, 327, 328, 330, 332, 333, 334, 335, 337, 338, 345, 346, 347, 348, 349, 351, 352, 353, 354, 355, 356, 357, 358, 360, 362, 363, 364], "branches": [[313, 314], [313, 316], [322, 323], [322, 333], [334, 335], [334, 364], [336, 345], [352, 353]]}

import pytest
from isort.wrap_modes import hanging_indent_with_parentheses


def test_hanging_indent_with_parentheses_empty_imports():
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
        "imports": ["very_long_import_name"],
        "line_length": 20,
        "statement": "from mod import ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "indent": "    ",
        "include_trailing_comma": True,
    }
    # line_length_limit = 19
    # statement initially "from mod import (" -> len is 16
    # next_statement = "from mod import (very_long_import_name" -> len 37 > 19
    # Triggers line 322-333 (first import exceeds limit)
    res = hanging_indent_with_parentheses(**interface)
    assert res is not None


def test_hanging_indent_with_parentheses_multiple_imports_with_comment_branch():
    interface = {
        "imports": ["b", "c"],
        "line_length": 80,
        "statement": "from mod import a",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "indent": "    ",
        "include_trailing_comma": True,
    }
    # statement initially "from mod import a("
    # next_import = "b" -> next_statement = "from mod import a(b"
    # while loop 1: next_import = "c"
    # test branch: line_separator not in interface['statement'] and '#' in interface['statement']
    interface["statement"] = "from mod import a(# comment"
    interface["imports"] = ["c"]
    
    res = hanging_indent_with_parentheses(**interface)
    assert res is not None


def test_hanging_indent_with_parentheses_current_line_exceeds_limit():
    interface = {
        "imports": ["a", "very_long_second_import_name_to_trigger_wrap"],
        "line_length": 30,
        "statement": "from mod import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "indent": "    ",
        "include_trailing_comma": False,
    }
    res = hanging_indent_with_parentheses(**interface)
    assert res is not None
