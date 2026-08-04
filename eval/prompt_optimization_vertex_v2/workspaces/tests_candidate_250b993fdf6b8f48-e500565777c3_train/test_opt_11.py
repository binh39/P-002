# file: src\sample_repo\isort\isort\wrap_modes.py:271-308
# asked: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 307, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 307], [306, 308]]}
# gained: {"lines": [271, 272, 273, 274, 276, 277, 278, 280, 281, 282, 283, 284, 285, 286, 287, 288, 291, 292, 294, 295, 296, 297, 298, 299, 301, 303, 304, 306, 308], "branches": [[273, 274], [273, 276], [282, 283], [282, 306], [290, 294], [290, 304], [306, 308]]}

from isort.wrap_modes import vertical_prefix_from_module_import

def test_vertical_prefix_from_module_import_empty():
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

def test_vertical_prefix_from_module_import_single_and_multiple():
    # Test execution of loop, line length wrapping, and comments condition at the end
    interface = {
        "imports": ["a", "b", "c"],
        "statement": "from module import ",
        "comments": ["# a comment"],
        "remove_comments": [],
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 25,  # Force wrap when combining
    }
    res = vertical_prefix_from_module_import(**interface)
    assert isinstance(res, str)
    assert "from module import a" in res
