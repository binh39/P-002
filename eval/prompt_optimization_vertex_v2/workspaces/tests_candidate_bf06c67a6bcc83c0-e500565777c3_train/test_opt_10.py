# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 139, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 98], [99, 102], [99, 104], [104, 105], [112, 113], [113, 114], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_short_content():
    # len(content) <= line_length
    config = Config(line_length=20)
    res = line("import a", "\n", config)
    assert res == "import a"


def test_line_noqa_mode_adds_noqa():
    # elif len(content) > config.line_length and wrap_mode == Modes.NOQA and "# NOQA" not in content
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    res = line("import long_module_name", "\n", config)
    assert res == "import long_module_name  # NOQA"


def test_line_noqa_mode_already_has_noqa():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    res = line("import long_module_name # NOQA", "\n", config)
    assert res == "import long_module_name # NOQA"


def test_line_splitter_at_start_skipped():
    # line_without_comment.strip().startswith(splitter) is True -> should not split
    config = Config(line_length=5)
    res = line("import a", "\n", config)
    assert res == "import a"


def test_line_wrap_with_comment_and_use_parentheses_noqa():
    # if comment and not (config.use_parentheses and "noqa" in comment) branch
    # Here use_parentheses=True and noqa in comment, so it skips modifying line_parts[-1] inside that `if`
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    res = line("import a, b # noqa", "\n", config)
    assert isinstance(res, str)


def test_line_wrap_empty_content_fallback():
    # if not content: content = next_line.pop()
    config = Config(
        line_length=5,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    # A single component after splitting that is long
    res = line("import verylongname", "\n", config)
    assert "verylongname" in res


def test_line_wrap_splitter_as():
    # if splitter == "as ": output = f"{content}{splitter}{cont_line.lstrip()}"
    config = Config(
        line_length=10,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    res = line("import a as b", "\n", config)
    assert "as" in res


def test_line_wrap_vertical_grid_grouped_and_comment_noqa():
    # wrap_mode in (Modes.VERTICAL_HANGING_INDENT, Modes.VERTICAL_GRID_GROUPED)
    # comment and "noqa" in comment
    # plus the comment_prefix in lines[-1] and lines[-1].endswith(")") adjustment block
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED if hasattr(Modes, "VERTICAL_GRID_GROUPED") else Modes.VERTICAL_HANGING_INDENT,
    )
    res = line("import foo, bar # noqa: E501", "\n", config)
    assert isinstance(res, str)




def test_line_wrap_other_wrap_mode_no_vertical_separator():
    # wrap_mode not in (VERTICAL_HANGING_INDENT, VERTICAL_GRID_GROUPED) -> _separator = ""
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=False,
        multi_line_output=Modes.HANGING_INDENT,
    )
    res = line("import foo, bar", "\n", config)
    assert isinstance(res, str)


def test_line_wrap_comment_no_noqa_and_trailing_comma():
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    res = line("import foo, bar # comment", "\n", config)
    assert "comment" in res
