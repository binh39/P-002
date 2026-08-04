# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_short_content():
    # len(content) <= config.line_length -> returns content
    config = Config(line_length=50)
    res = line("import os", "\n", config)
    assert res == "import os"


def test_line_noqa_mode_adds_noqa():
    # len(content) > config.line_length and wrap_mode == Modes.NOQA and "# NOQA" not in content
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    res = line("import very_long_module_name", "\n", config)
    assert res == f"import very_long_module_name{config.comment_prefix} NOQA"


def test_line_noqa_mode_already_has_noqa():
    # len(content) > config.line_length and wrap_mode == Modes.NOQA and "# NOQA" in content -> returns content
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import very_long_module_name # NOQA"
    res = line(content, "\n", config)
    assert res == content


def test_line_splitter_not_matching():
    # len(content) > config.line_length, wrap_mode != Modes.NOQA, but no matching splitter
    config = Config(line_length=10)
    content = "very_long_string_without_splitter"
    res = line(content, "\n", config)
    assert res == content


def test_line_splitter_at_start():
    # line_without_comment.strip().startswith(splitter) is True -> doesn't split
    config = Config(line_length=10)
    content = "import long_module_name"
    res = line(content, "\n", config)
    assert res == content


def test_line_basic_wrap_backslash():
    # use_parentheses = False, splitter in content
    config = Config(line_length=15, use_parentheses=False)
    content = "from module import a, b, c, d"
    res = line(content, "\n", config)
    assert "\\" in res


def test_line_use_parentheses_as_splitter():
    # splitter == "as " with use_parentheses = True
    config = Config(line_length=10, use_parentheses=True)
    content = "import very_long_name as vln"
    res = line(content, "\n", config)
    assert "as" in res


def test_line_use_parentheses_comment_without_noqa():
    # comment exists, use_parentheses=True, "noqa" not in comment
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
    )
    content = "from module import name # Some comment"
    res = line(content, "\n", config)
    assert "# Some comment" in res


def test_line_use_parentheses_comment_with_noqa():
    # comment exists, use_parentheses=True, "noqa" in comment
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
    )
    content = "from module import name # noqa: E501"
    res = line(content, "\n", config)
    assert "noqa" in res


def test_line_vertical_hanging_indent_mode():
    # wrap_mode in (Modes.VERTICAL_HANGING_INDENT, Modes.VERTICAL_GRID_GROUPED)
    config = Config(
        line_length=15,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        include_trailing_comma=True,
    )
    content = "from module import a, b, c, d"
    res = line(content, "\n", config)
    assert "\n" in res


def test_line_vertical_grid_grouped_mode():
    config = Config(
        line_length=15,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
        include_trailing_comma=True,
    )
    content = "from module import a, b, c, d"
    res = line(content, "\n", config)
    assert "\n" in res


def test_line_comment_prefix_in_last_line_with_parentheses():
    # triggers: if config.comment_prefix in lines[-1] and lines[-1].endswith(")"):
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=False,
    )
    content = "import a.b as c # comment"
    res = line(content, "\n", config)
    assert ")" in res


def test_line_empty_content_after_while_loop():
    # triggers: if not content: content = next_line.pop()
    config = Config(line_length=2, use_parentheses=False)
    content = "a.b"
    res = line(content, "\n", config)
    assert res is not None
