# file: src\sample_repo\isort\isort\wrap_modes.py:311-364
# asked: {"lines": [311, 312, 313, 314, 316, 318, 319, 320, 322, 323, 324, 325, 326, 327, 328, 330, 332, 333, 334, 335, 337, 338, 340, 341, 342, 345, 346, 347, 348, 349, 351, 352, 353, 354, 355, 356, 357, 358, 360, 362, 363, 364], "branches": [[313, 314], [313, 316], [322, 323], [322, 333], [334, 335], [334, 364], [336, 340], [336, 345], [352, 353], [352, 363]]}
# gained: {"lines": [311, 312, 313, 314, 316, 318, 319, 320, 322, 323, 324, 325, 326, 327, 328, 330, 332, 333, 334, 335, 337, 345, 346, 347, 348, 349, 351, 352, 353, 354, 355, 356, 357, 358, 360, 362, 363, 364], "branches": [[313, 314], [313, 316], [322, 323], [334, 335], [334, 364], [336, 345], [352, 353]]}

import pytest
from isort.wrap_modes import hanging_indent_with_parentheses

def test_hanging_indent_with_parentheses_empty():
    interface = {
        "imports": [],
        "statement": "from module import ",
        "line_length": 80,
        "indent": "    ",
        "line_separator": "\n",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "include_trailing_comma": False,
    }
    assert hanging_indent_with_parentheses(**interface) == ""

def test_hanging_indent_with_parentheses_first_import_overflow():
    interface = {
        "imports": ["very_long_import_name_that_exceeds_limit"],
        "statement": "from module import ",
        "line_length": 25,
        "indent": "    ",
        "line_separator": "\n",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": "#",
        "include_trailing_comma": True,
    }
    res = hanging_indent_with_parentheses(**interface)
    assert "(" in res
    assert "very_long_import_name_that_exceeds_limit" in res

def test_hanging_indent_with_parentheses_loop_branches():
    # Test multiple imports, where:
    # 1. '# in interface["statement"]' and not line_separator in statement (branch at line 336)
    # 2. current_line exceeds line_length_limit (branch at line 352)
    interface = {
        "imports": ["b", "c_very_long_import_name_to_trigger_overflow"],
        "statement": "from module import a # comment",
        "line_length": 30,
        "indent": "    ",
        "line_separator": "\n",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "include_trailing_comma": True,
    }
    res = hanging_indent_with_parentheses(**interface)
    assert res.endswith(")")
    assert "b" in res
    assert "c_very_long_import_name_to_trigger_overflow" in res
