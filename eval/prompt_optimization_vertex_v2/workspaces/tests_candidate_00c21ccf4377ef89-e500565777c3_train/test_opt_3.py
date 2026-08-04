# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [146, 147], [146, 167], [153, 156], [153, 157]]}

from isort.wrap_modes import hanging_indent

def test_hanging_indent_empty_imports():
    interface = {
        "imports": [],
        "statement": "import os",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    assert hanging_indent(**interface) == ""

def test_hanging_indent_first_import_exceeds_limit():
    interface = {
        "imports": ["very_long_import_name_that_exceeds_limit"],
        "statement": "from module import ",
        "line_length": 20,  # line_length_limit = 17
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "\n" in result

def test_hanging_indent_multiple_imports_line_wrap_and_comments():
    interface = {
        "imports": ["a", "b" * 30],
        "statement": "from mod import ",
        "line_length": 25,  # line_length_limit = 22
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "mod" in result

def test_hanging_indent_comments_fits_on_line():
    interface = {
        "imports": ["a"],
        "statement": "import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "# comment" in result

def test_hanging_indent_comments_exceeds_line_with_comment():
    interface = {
        "imports": ["a"],
        "statement": "import " + "a" * 70,
        "line_length": 40,  # line_length_limit = 37
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# comment"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "\n" in result
