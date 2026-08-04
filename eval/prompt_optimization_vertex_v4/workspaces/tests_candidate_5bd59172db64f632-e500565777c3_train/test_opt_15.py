# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [112, 113], [112, 140], [113, 114], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_short_content():
    config = Config(line_length=40)
    res = line("import os", "\n", config)
    assert res == "import os"


def test_line_noqa_mode_adds_comment():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import os_very_long_name"
    assert len(content) > config.line_length
    res = line(content, "\n", config)
    assert "NOQA" in res


def test_line_noqa_mode_already_has_noqa():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import os_very_long_name # NOQA"
    res = line(content, "\n", config)
    assert res == content


def test_line_wrap_with_splitter_no_parentheses():
    config = Config(
        line_length=15,
        wrap_length=15,
        use_parentheses=False,
        multi_line_output=Modes.GRID,
    )
    content = "from my_module import a, b, c"
    res = line(content, "\n", config)
    assert "\\" in res
    assert "import" in res


def test_line_wrap_with_comment_and_no_parentheses_or_use_parentheses():
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "import a as b # comment"
    res = line(content, "\n", config)
    assert "as" in res


def test_line_wrap_splitter_as_with_parentheses():
    config = Config(
        line_length=10,
        use_parentheses=True,
        multi_line_output=Modes.GRID,
    )
    content = "import long_module_name as lmn"
    res = line(content, "\n", config)
    assert "as" in res




def test_line_wrap_comment_fixup_at_end():
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=False,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        comment_prefix="#",
    )
    content = "import a, b, c # mycomment"
    res = line(content, "\n", config)
    assert "#" in res


def test_line_empty_content_after_pop():
    config = Config(
        line_length=5,
        wrap_length=2,
        use_parentheses=False,
        multi_line_output=Modes.GRID,
    )
    content = "import a"
    res = line(content, "\n", config)
    assert res is not None


def test_line_splitter_at_start():
    config = Config(
        line_length=5,
        use_parentheses=False,
        multi_line_output=Modes.GRID,
    )
    content = "import_something_long_without_space"
    res = line(content, "\n", config)
    assert res == content
