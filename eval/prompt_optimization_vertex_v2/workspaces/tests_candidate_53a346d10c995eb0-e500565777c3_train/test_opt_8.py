# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156]]}

from isort.wrap_modes import hanging_indent


def test_hanging_indent_empty_imports():
    interface = {
        "imports": [],
        "statement": "from module import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert result == ""


def test_hanging_indent_first_import_exceeds_limit():
    interface = {
        "imports": ["very_long_import_name_that_exceeds_limit"],
        "statement": "from module import ",
        "line_length": 20,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # line_length_limit = 20 - 3 = 17
    # "from module import very_long_import_name_that_exceeds_limit" len > 17
    result = hanging_indent(**interface)
    assert "very_long_import_name_that_exceeds_limit" in result


def test_hanging_indent_multiple_imports_and_line_splitting():
    interface = {
        "imports": ["a", "b", "c_very_long_import_name_to_trigger_split"],
        "statement": "import ",
        "line_length": 15,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # line_length_limit = 15 - 3 = 12
    result = hanging_indent(**interface)
    assert isinstance(result, str)
    assert "c_very_long_import_name_to_trigger_split" in result


def test_hanging_indent_with_comments_fits():
    interface = {
        "imports": ["a"],
        "statement": "import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["comment"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert "# comment" in result




def test_hanging_indent_no_comments_returns_statement():
    interface = {
        "imports": ["a"],
        "statement": "import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    result = hanging_indent(**interface)
    assert result == "import a"
