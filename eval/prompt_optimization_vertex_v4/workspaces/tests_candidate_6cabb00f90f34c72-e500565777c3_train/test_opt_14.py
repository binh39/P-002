# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}

import pytest
from isort.wrap_modes import vertical_prefix_from_module_import

def test_vertical_prefix_from_module_import_empty_imports():
    # Covers line 273-274: not interface["imports"]
    interface = {
        "imports": [],
        "statement": "from mod import ",
        "comments": [],
        "remove_comments": [],
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
    }
    result = vertical_prefix_from_module_import(**interface)
    assert result == ""

def test_vertical_prefix_from_module_import_single_import():
    # Covers when there is 1 import (loop doesn't run, comments and statement_with_comments not both truthy)
    interface = {
        "imports": ["a"],
        "statement": "from mod import ",
        "comments": [],
        "remove_comments": [],
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
    }
    result = vertical_prefix_from_module_import(**interface)
    assert result == "from mod import a"

def test_vertical_prefix_from_module_import_wrap_exceeded():
    # Covers the wrap condition inside the loop (lines 290-303)
    # where length exceeds line_length, triggering wrapping and resetting comments
    interface = {
        "imports": ["a", "b"],
        "statement": "from mod import ",
        "comments": ["# comment"],
        "remove_comments": [],
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 15, # very short line length to force wrap on second import
    }
    result = vertical_prefix_from_module_import(**interface)
    # First iteration: output_statement = "from mod import a"
    # Second iteration: statement = "from mod import a, b" + comment -> exceeds line_length 15
    assert "from mod import a" in result
    assert "b" in result

def test_vertical_prefix_from_module_import_comments_and_statement_with_comments():
    # Covers lines 306-307: if comments and statement_with_comments: output_statement = statement_with_comments
    interface = {
        "imports": ["a", "b"],
        "statement": "from mod import ",
        "comments": ["# comment"],
        "remove_comments": [],
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80, # long enough not to wrap
    }
    result = vertical_prefix_from_module_import(**interface)
    # comments remain present, statement_with_comments was computed during the loop
    assert "# comment" in result
    assert "a, b" in result
