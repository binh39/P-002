# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [141, 142], [141, 144]]}

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
    res = line("import very_long_module_name", "\n", config)
    assert res == f"import very_long_module_name{config.comment_prefix} NOQA"


def test_line_noqa_mode_already_has_noqa():
    # len(content) > config.line_length and wrap_mode == Modes.NOQA and "# NOQA" in content -> returns content unchanged
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    res = line("import very_long_module_name # NOQA", "\n", config)
    assert res == "import very_long_module_name # NOQA"


def test_line_wrap_splitter_dot_no_parentheses():
    # Splitter "." with use_parentheses=False
    config = Config(line_length=10, use_parentheses=False, line_ending="\n")
    res = line("very.long.module.name", "\n", config)
    assert "\\" in res


def test_line_wrap_splitter_as_with_parentheses():
    # Splitter "as " with use_parentheses=True
    config = Config(line_length=10, use_parentheses=True, include_trailing_comma=True)
    res = line("import a as very_long_alias_name", "\n", config)
    assert "as" in res


def test_line_wrap_splitter_import_with_comment_and_noqa():
    # Comment with "noqa", use_parentheses=True, vertical hanging indent
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    res = line("import alpha, beta # noqa: E501", "\n", config)
    assert "noqa" in res


def test_line_wrap_splitter_import_with_comment_no_noqa_and_vertical_grid_grouped():
    # Comment without "noqa", VERTICAL_GRID_GROUPED mode, comment_prefix in lines[-1] and ends with ')'
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
        comment_prefix="#",
    )
    # Make sure content splits with "import ", has a comment, and triggers lines[-1] ending with ')'
    res = line("import foo, bar # mycomment", "\n", config)
    assert "# mycomment" in res


def test_line_wrap_empty_content_after_pop():
    # Forces `if not content: content = next_line.pop()`
    config = Config(
        line_length=1,
        use_parentheses=False,
    )
    res = line("a.b", "\n", config)
    assert res is not None


def test_line_splitter_starts_with_splitter():
    # line_without_comment.strip().startswith(splitter) -> True, so should skip that splitter and try others
    config = Config(line_length=10, use_parentheses=False)
    res = line("import .b", "\n", config)
    assert res == "import .b"
