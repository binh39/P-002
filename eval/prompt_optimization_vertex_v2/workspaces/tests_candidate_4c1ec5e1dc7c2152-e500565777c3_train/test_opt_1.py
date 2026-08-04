# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [146, 147], [146, 167], [153, 156], [153, 157]]}

from isort.wrap_modes import hanging_indent


def test_hanging_indent_empty_imports():
    interface = {
        "imports": [],
        "statement": "import a",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    assert hanging_indent(**interface) == ""


def test_hanging_indent_basic_and_wrapping():
    # Test first import too long (> line_length_limit)
    # line_length = 10, limit = 7. statement = "import ", next_import = "longimport" -> len(statement + next_import) = 15 > 7
    interface = {
        "imports": ["longimport"],
        "statement": "import ",
        "line_length": 10,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    res = hanging_indent(**interface)
    assert "\n" in res


def test_hanging_indent_loop_and_subsequent_wrap():
    # Test multiple imports, where subsequent import causes line wrap inside the while loop
    # line_length = 15, limit = 12
    interface = {
        "imports": ["a", "verylongimportname"],
        "statement": "import ",
        "line_length": 15,
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    res = hanging_indent(**interface)
    assert "verylongimportname" in res


def test_hanging_indent_comments_fitting_and_overflow():
    # Test comments fitting within line length limit + 2
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
    res1 = hanging_indent(**interface)
    assert "# comment" in res1

    # Test comments overflowing line length limit + 2 (lines 157-164)
    interface_overflow = {
        "imports": ["a"],
        "statement": "import a",
        "line_length": 12,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["very long comment that exceeds the limit"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    res2 = hanging_indent(**interface_overflow)
    assert "\n" in res2
    assert "very long comment" in res2
