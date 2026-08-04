# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [306, 308]]}

import pytest
from isort.wrap_modes import vertical_prefix_from_module_import


def test_vertical_prefix_from_module_import_empty_imports():
    interface = {
        "imports": [],
        "statement": "from mod import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
    }
    result = vertical_prefix_from_module_import(**interface)
    assert result == ""


def test_vertical_prefix_from_module_import_normal_and_wrapping():
    # Test multiple imports, triggering line length wrapping, and the final if comments and statement_with_comments check.
    interface = {
        "imports": ["a", "b", "c"],
        "statement": "from mod import ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 18,  # Forces wrapping early
    }
    result = vertical_prefix_from_module_import(**interface)
    assert isinstance(result, str)
    assert "a" in result
    assert "b" in result
    assert "c" in result
