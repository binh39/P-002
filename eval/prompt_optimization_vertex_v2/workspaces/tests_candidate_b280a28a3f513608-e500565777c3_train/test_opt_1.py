# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [146, 147], [146, 167], [153, 156], [153, 157]]}

import pytest
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


def test_hanging_indent_first_import_exceeds_limit():
    interface = {
        "imports": ["b"],
        "statement": "from a import ",
        "line_length": 15,  # limit = 12
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # next_statement length > 12 -> triggers line 127/128
    res = hanging_indent(**interface)
    assert "b" in res


def test_hanging_indent_subsequent_import_exceeds_limit():
    interface = {
        "imports": ["bbb", "ccc"],
        "statement": "import ",
        "line_length": 15,  # limit = 12
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    res = hanging_indent(**interface)
    assert "bbb" in res
    assert "ccc" in res


def test_hanging_indent_with_comments_fits():
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
    res = hanging_indent(**interface)
    assert "# comment" in res


def test_hanging_indent_with_comments_exceeds_limit():
    interface = {
        "imports": ["a"],
        "statement": "import ",
        "line_length": 15,  # limit = 12
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["# a very long comment that exceeds limit"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    res = hanging_indent(**interface)
    assert "\n" in res
    assert "a very long comment" in res
