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
        "remove_comments": [],
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
    }
    assert vertical_prefix_from_module_import(**interface) == ""

def test_vertical_prefix_from_module_import_basic():
    interface = {
        "imports": ["a", "b", "c"],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": [],
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
    }
    result = vertical_prefix_from_module_import(**interface)
    assert result == "from module import a, b, c"

def test_vertical_prefix_from_module_import_line_length_exceeded():
    interface = {
        "imports": ["very_long_import_name_one", "very_long_import_name_two"],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": [],
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 30,
    }
    result = vertical_prefix_from_module_import(**interface)
    assert "very_long_import_name_one" in result
    assert "very_long_import_name_two" in result
    assert "\n" in result

def test_vertical_prefix_from_module_import_with_comments_triggering_last_if():
    interface = {
        "imports": ["a", "b"],
        "statement": "from module import ",
        "comments": ["# comment"],
        "remove_comments": [],
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
    }
    result = vertical_prefix_from_module_import(**interface)
    # This hits: if comments and statement_with_comments: output_statement = statement_with_comments
    assert "from module import a, b" in result
