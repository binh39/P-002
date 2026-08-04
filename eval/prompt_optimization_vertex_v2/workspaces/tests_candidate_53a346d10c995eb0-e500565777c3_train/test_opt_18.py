# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}

import pytest
from isort.wrap_modes import vertical_prefix_from_module_import

def test_vertical_prefix_from_module_import_empty_imports():
    interface = {
        "imports": [],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
    }
    assert vertical_prefix_from_module_import(**interface) == ""

def test_vertical_prefix_from_module_import_normal():
    interface = {
        "imports": ["a", "b"],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
    }
    result = vertical_prefix_from_module_import(**interface)
    assert "a" in result and "b" in result

def test_vertical_prefix_from_module_import_exceeds_line_length():
    interface = {
        "imports": ["long_import_name_a", "long_import_name_b"],
        "statement": "from module import ",
        "comments": ["# a comment"],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 25,  # Force line length overflow inside the loop
    }
    result = vertical_prefix_from_module_import(**interface)
    assert "long_import_name_a" in result
    assert "long_import_name_b" in result

def test_vertical_prefix_from_module_import_comments_and_statement_with_comments():
    interface = {
        "imports": ["a", "b"],
        "statement": "from module import ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
    }
    result = vertical_prefix_from_module_import(**interface)
    assert "# comment" in result
