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
    result = vertical_prefix_from_module_import(**interface)
    assert result == ""


def test_vertical_prefix_from_module_import_no_wrap_no_comments():
    interface = {
        "imports": ["a", "b", "c"],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
    }
    result = vertical_prefix_from_module_import(**interface)
    assert result == "from module import a, b, c"


def test_vertical_prefix_from_module_import_with_wrap():
    interface = {
        "imports": ["a", "b", "c"],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 25,  # Forces wrapping
    }
    result = vertical_prefix_from_module_import(**interface)
    # With line_length 25, "from module import a, b" exceeds length or similar, triggering the if branch on line 290
    assert isinstance(result, str)
    assert "from module import" in result


def test_vertical_prefix_from_module_import_with_comments_and_statement_with_comments():
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
    # Triggers comments and statement_with_comments truthy on line 306
    assert "from module import a, b" in result
    assert "# comment" in result
