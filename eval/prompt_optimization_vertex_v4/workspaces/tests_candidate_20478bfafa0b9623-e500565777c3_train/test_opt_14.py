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
    # Modifies/pops, so pass a copy or handle list
    res = vertical_prefix_from_module_import(**interface)
    assert res == ""

def test_vertical_prefix_from_module_import_no_wrap():
    interface = {
        "imports": ["a", "b"],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
    }
    res = vertical_prefix_from_module_import(**interface)
    assert res == "from module import a, b"

def test_vertical_prefix_from_module_import_with_wrap_and_comments():
    interface = {
        "imports": ["a", "long_import_to_trigger_wrap"],
        "statement": "from module import ",
        "comments": ["# a comment"],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 25,
    }
    res = vertical_prefix_from_module_import(**interface)
    # This should trigger the line-length exceed branch inside the loop
    # and also test the final `if comments and statement_with_comments:` block.
    assert "from module import a" in res
    assert "long_import_to_trigger_wrap" in res
