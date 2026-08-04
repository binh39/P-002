# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 308]]}

from isort.wrap_modes import vertical_prefix_from_module_import

def test_vertical_prefix_from_module_import_basic():
    interface = {
        "statement": "from module import ",
        "imports": ["a", "b", "c"],
        "comments": [],
        "remove_comments": [],
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
    }
    result = vertical_prefix_from_module_import(**interface)
    assert result == "from module import a, b, c"

def test_vertical_prefix_from_module_import_empty_imports():
    interface = {
        "statement": "from module import ",
        "imports": [],
        "comments": [],
        "remove_comments": [],
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
    }
    result = vertical_prefix_from_module_import(**interface)
    assert result == ""

def test_vertical_prefix_from_module_import_wrapping_and_comments():
    interface = {
        "statement": "from module import ",
        "imports": ["alpha", "beta", "gamma"],
        "comments": ["# comment"],
        "remove_comments": [],
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 25,
    }
    result = vertical_prefix_from_module_import(**interface)
    # This should trigger the line-length wrapping branch inside the loop (lines 290-303)
    # and the final conditional (lines 306-307)
    assert "alpha" in result
    assert "beta" in result
    assert "gamma" in result
    assert "\n" in result
