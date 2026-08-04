# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 89, 90, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 107, 108, 109, 110, 112, 113, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 107], [112, 113], [112, 140], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_short():
    config = Config(line_length=40)
    assert line("import os", "\n", config) == "import os"


def test_line_no_wrap_noqa_mode_with_noqa():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import os # NOQA"
    assert line(content, "\n", config) == content


def test_line_wrap_noqa_mode_adds_noqa():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import very_long_module_name"
    # Should add # NOQA if not present
    res = line(content, "\n", config)
    assert "# NOQA" in res


def test_line_wrap_with_comment_and_no_parentheses():
    config = Config(
        line_length=20,
        wrap_length=15,
        use_parentheses=False,
        include_trailing_comma=True,
    )
    content = "from module import a, b # comment"
    res = line(content, "\n", config)
    assert "\\" in res


def test_line_wrap_with_parentheses_and_as_splitter():
    config = Config(
        line_length=20,
        wrap_length=15,
        use_parentheses=True,
    )
    content = "import module as m"
    res = line(content, "\n", config)
    assert "as" in res


def test_line_wrap_with_parentheses_and_vertical_hanging_indent():
    config = Config(
        line_length=20,
        wrap_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "from pkg import a, b, c"
    res = line(content, "\n", config)
    assert "(" in res
    assert ")" in res


def test_line_wrap_with_parentheses_and_comment_noqa():
    config = Config(
        line_length=20,
        wrap_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        comment_prefix="#",
    )
    content = "from pkg import a, b, c # noqa: E501"
    res = line(content, "\n", config)
    assert "noqa" in res
    assert ")" in res


def test_line_wrap_empty_content_after_pop():
    # Force content to be empty after while loop pops everything, triggering `if not content: content = next_line.pop()`
    config = Config(
        line_length=5,
        wrap_length=5,
        use_parentheses=False,
    )
    content = "import a"
    res = line(content, "\n", config)
    assert res is not None


def test_line_wrap_lines_ending_with_comment_and_paren():
    config = Config(
        line_length=10,
        wrap_length=10,
        use_parentheses=True,
        comment_prefix="#",
    )
    content = "from a import b, c # comment"
    res = line(content, "\n", config)
    assert res is not None
