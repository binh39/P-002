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
        "imports": ["long_module_name_to_exceed_limit"],
        "statement": "from module import ",
        "line_length": 20,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # line_length_limit = 20 - 3 = 17
    # "from module import long_module_name_to_exceed_limit" > 17
    result = hanging_indent(**interface)
    assert "long_module_name_to_exceed_limit" in result
    assert "\n" in result


def test_hanging_indent_multiple_imports_and_wrap():
    interface = {
        "imports": ["a", "very_long_import_that_exceeds_line_limit_definitely"],
        "statement": "import ",
        "line_length": 30,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # Tests loop execution, first import 'a', second import triggering wrap.
    result = hanging_indent(**interface)
    assert "very_long_import_that_exceeds_line_limit_definitely" in result


def test_hanging_indent_with_comments_fits():
    interface = {
        "imports": ["os"],
        "statement": "import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["comment"],
        "remove_comments": False,
        "comment_prefix": "# ",
    }
    result = hanging_indent(**interface)
    assert "os" in result
    assert "comment" in result


def test_hanging_indent_with_comments_exceeds_limit():
    interface = {
        "imports": ["os"],
        "statement": "import ",
        "line_length": 15,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["very_long_comment_exceeding_line_length"],
        "remove_comments": False,
        "comment_prefix": "# ",
    }
    # line_length_limit = 15 - 3 = 12
    # statement_with_comments will exceed line_length_limit + 2
    result = hanging_indent(**interface)
    assert "\n" in result
    assert "very_long_comment_exceeding_line_length" in result
