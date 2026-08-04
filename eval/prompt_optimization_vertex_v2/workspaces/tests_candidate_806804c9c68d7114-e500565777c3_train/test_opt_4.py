# file: src\sample_repo\isort\isort\wrap_modes.py:117-167
# asked: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}
# gained: {"lines": [117, 118, 119, 120, 122, 124, 125, 127, 128, 129, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141, 142, 144, 146, 147, 148, 149, 150, 151, 153, 154, 156, 157, 158, 159, 160, 161, 162, 163, 164, 167], "branches": [[119, 120], [119, 122], [127, 128], [127, 135], [136, 137], [136, 146], [139, 140], [139, 144], [146, 147], [146, 167], [153, 156], [153, 157]]}

import pytest
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
        "imports": ["sys"],
        "statement": "import ",
        "line_length": 10,  # line_length_limit = 7
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # "import sys" len is 10 > 7, so it triggers line 127 branch
    res = hanging_indent(**interface)
    assert "sys" in res


def test_hanging_indent_multiple_imports_and_overflow():
    interface = {
        "imports": ["os", "sys", "math"],
        "statement": "from module import ",
        "line_length": 20,  # line_length_limit = 17
        "line_separator": "\n",
        "indent": "    ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    # Should trigger while loop, multiple imports, and internal line length checks (line 139)
    res = hanging_indent(**interface)
    assert isinstance(res, str)
    assert "os" in res
    assert "sys" in res
    assert "math" in res


def test_hanging_indent_with_comments_fits():
    interface = {
        "imports": ["os"],
        "statement": "import ",
        "line_length": 80,
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["comment"],
        "remove_comments": False,
        "comment_prefix": "#",
    }
    res = hanging_indent(**interface)
    assert "# comment" in res


def test_hanging_indent_with_comments_overflow():
    interface = {
        "imports": ["os", "sys", "math", "collections", "itertools"],
        "statement": "from a_very_long_module_name import ",
        "line_length": 30,  # limit = 27
        "line_separator": "\n",
        "indent": "    ",
        "comments": ["a very long comment that forces wrap"],
        "remove_comments": False,
        "comment_prefix": "# ",
    }
    res = hanging_indent(**interface)
    assert isinstance(res, str)
    assert "a very long comment" in res
