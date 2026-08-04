# file: src\sample_repo\isort\isort\wrap_modes.py:311-364
# asked: {"lines": [311, 312, 313, 314, 316, 318, 319, 320, 322, 323, 324, 325, 326, 327, 328, 330, 332, 333, 334, 335, 337, 338, 340, 341, 342, 345, 346, 347, 348, 349, 351, 352, 353, 354, 355, 356, 357, 358, 360, 362, 363, 364], "branches": [[313, 314], [313, 316], [322, 323], [322, 333], [334, 335], [334, 364], [336, 340], [336, 345], [352, 353], [352, 363]]}
# gained: {"lines": [311, 312, 313, 314, 316, 318, 319, 320, 322, 323, 324, 325, 326, 327, 328, 330, 332, 333, 334, 364], "branches": [[313, 314], [313, 316], [322, 323], [322, 333], [334, 364]]}

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


def test_hanging_indent_with_parentheses_first_import_overflow():
    interface = {
        "imports": ["long_import_name"],
        "line_length": 15,
        "statement": "from module import ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "indent": "    ",
        "include_trailing_comma": True,
    }
    # "from module import (long_import_name" length is > 15-1=14
    res = hanging_indent_with_parentheses(**interface)
    assert "long_import_name" in res
    assert res.endswith(")")


def test_hanging_indent_with_parentheses_while_loop_with_hash():
    interface = {
        "imports": ["import_two", "import_three"],
        "line_length": 80,
        "statement": "from module import import_one",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "indent": "    ",
        "include_trailing_comma": False,
    }
    # Manually inject a hash in statement without line_separator
    interface["statement"] = "from module import import_one # comment"
    interface["imports"] = ["import_two"]
    res = hanging_indent_with_parentheses(**interface)
    assert "import_two" in res


def test_hanging_indent_with_parentheses_current_line_overflow():
    interface = {
        "imports": ["a_very_long_second_import_name"],
        "line_length": 20,
        "statement": "from mod import imp1",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "indent": "    ",
        "include_trailing_comma": False,
    }
    res = hanging_indent_with_parentheses(**interface)
    assert "\n    a_very_long_second_import_name" in res
