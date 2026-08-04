# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 308]]}

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
    # Test line 273: if not interface["imports"]: return ""
    assert vertical_prefix_from_module_import(**interface) == ""

def test_vertical_prefix_from_module_import_basic_and_line_length_exceeded():
    # This will exercise the loop, wrapping branch (line 290 onwards), and comments & statement_with_comments at the end (line 306)
    interface = {
        "imports": ["a", "b", "c"],
        "statement": "from mod import ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 15, # Force line length exceedance quickly
    }
    res = vertical_prefix_from_module_import(**interface)
    assert isinstance(res, str)
    assert "from mod import" in res

def test_vertical_prefix_from_module_import_no_comments_at_end():
    # Exercises when comments is empty or statement_with_comments is empty at line 306
    interface = {
        "imports": ["a", "b"],
        "statement": "from mod import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
    }
    res = vertical_prefix_from_module_import(**interface)
    assert res == "from mod import a, b"
