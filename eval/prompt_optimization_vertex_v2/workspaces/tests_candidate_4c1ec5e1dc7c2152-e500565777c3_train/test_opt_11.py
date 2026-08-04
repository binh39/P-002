# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [306, 308]]}

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
    result = vertical_prefix_from_module_import(**interface)
    assert result == ""

def test_vertical_prefix_from_module_import_basic_and_wrapping_and_comments():
    # This test exercises:
    # 1. Non-empty imports with multiple items triggering the loop (lines 282-304).
    # 2. Line length exceeded inside the loop triggering lines 291-303 (wrapping).
    # 3. Final `if comments and statement_with_comments:` condition (lines 306-307).
    interface = {
        "imports": ["alpha", "beta", "gamma"],
        "statement": "from mod import ",
        "comments": ["# a comment"],
        "remove_comments": [],
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 25,  # small enough to trigger wrap on second/third import
    }
    result = vertical_prefix_from_module_import(**interface)
    assert isinstance(result, str)
    assert "alpha" in result
    assert "beta" in result
    assert "gamma" in result
