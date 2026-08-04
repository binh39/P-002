# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 125, 126, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [126, 130], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_short_content():
    config = Config(line_length=40)
    res = line("import os", "\n", config)
    assert res == "import os"


def test_line_noqa_mode():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    # len("import os") is 9 <= 10
    assert line("import os", "\n", config) == "import os"
    # len("import os and sys") is 17 > 10, but NOQA mode without '# NOQA'
    res = line("import os and sys", "\n", config)
    assert res == "import os and sys  # NOQA"

    # Already has '# NOQA'
    config2 = Config(line_length=10, multi_line_output=Modes.NOQA)
    assert line("import os and sys # NOQA", "\n", config2) == "import os and sys # NOQA"


def test_line_wrap_with_comment_and_parentheses_and_comma():
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "import a as b  # comment"
    res = line(content, "\n", config)
    assert "as" in res


def test_line_wrap_non_as_splitter_vertical_hanging_indent():
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "from module import foo, bar"
    res = line(content, "\n", config)
    assert "(" in res
    assert ")" in res


def test_line_wrap_vertical_grid_grouped_with_noqa_comment():
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    content = "import alpha, beta  # noqa: E401"
    res = line(content, "\n", config)
    assert "noqa" in res


def test_line_wrap_comment_prefix_in_lines_last_and_ends_with_paren():
    config = Config(
        line_length=5,
        use_parentheses=True,
        include_trailing_comma=False,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        comment_prefix="#",
    )
    content = "import a, b #c"
    res = line(content, "\n", config)
    assert isinstance(res, str)


def test_line_wrap_without_parentheses():
    config = Config(
        line_length=5,
        use_parentheses=False,
        multi_line_output=Modes.HANGING_INDENT,
    )
    content = "from package import module"
    res = line(content, "\n", config)
    assert "\\" in res


def test_line_splitter_dot():
    config = Config(
        line_length=8,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "package.subpackage.module"
    res = line(content, "\n", config)
    assert "." in res
