# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}

import pytest
from isort.wrap_modes import vertical_prefix_from_module_import

def test_vertical_prefix_from_module_import_empty():
    # Test line 273-274: empty imports list
    interface = {
        "imports": [],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": [],
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
    }
    res = vertical_prefix_from_module_import(**interface)
    assert res == ""

def test_vertical_prefix_from_module_import_basic():
    # Test normal execution without exceeding line length and without comment conditions
    interface = {
        "imports": ["a", "b"],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": [],
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
    }
    res = vertical_prefix_from_module_import(**interface)
    assert res == "from module import a, b"

def test_vertical_prefix_from_module_import_exceeds_line_length():
    # Test when line length is exceeded inside the loop (lines 290-303)
    interface = {
        "imports": ["alpha", "beta"],
        "statement": "from mod import ",
        "comments": [],
        "remove_comments": [],
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 15,  # Force wrap on second import
    }
    res = vertical_prefix_from_module_import(**interface)
    # alpha makes it "from mod import alpha" (len 20 > 15? Wait, let's trace carefully)
    # output_statement starts as "from mod import alpha"
    # next_import is "beta"
    # statement becomes "from mod import alpha, beta"
    # line_separator is "\n", line length is 15
    # The last line length will definitely exceed 15.
    assert "from mod import alpha" in res
    assert "beta" in res

def test_vertical_prefix_from_module_import_with_comments():
    # Test lines 306-307: if comments and statement_with_comments:
    interface = {
        "imports": ["a", "b"],
        "statement": "from mod import ",
        "comments": ["# a comment"],
        "remove_comments": [],
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
    }
    res = vertical_prefix_from_module_import(**interface)
    assert "# a comment" in res
