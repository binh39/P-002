# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [113, 114], [113, 116], [118, 122], [126, 127], [126, 130], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_short_content():
    # len(content) <= config.line_length -> returns content directly (line 144)
    config = Config(line_length=50)
    res = line("import a", "\n", config)
    assert res == "import a"


def test_line_noqa_mode_adds_noqa():
    # len(content) > config.line_length and wrap_mode == Modes.NOQA and '# NOQA' not in content (lines 141-142)
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    res = line("import very_long_module_name", "\n", config)
    assert res == f"import very_long_module_name{config.comment_prefix} NOQA"


def test_line_noqa_mode_already_has_noqa():
    # len(content) > config.line_length and wrap_mode == Modes.NOQA and '# NOQA' in content -> returns content (line 144)
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    res = line("import very_long_module_name # NOQA", "\n", config)
    assert res == "import very_long_module_name # NOQA"


def test_line_splitter_as_with_parentheses():
    # Tests splitter == 'as ' with use_parentheses = True (lines 79-115)
    config = Config(line_length=10, use_parentheses=True)
    res = line("import long_name as x", "\n", config)
    assert "as" in res


def test_line_splitter_dot_with_comment_noqa_parentheses():
    # Tests splitter == '.', comment with 'noqa', use_parentheses = True
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    # content has a comment with 'noqa'
    content = "very.long.module.name # noqa: E501"
    res = line(content, "\n", config)
    assert "noqa" in res


def test_line_vertical_grid_grouped_and_comment_processing():
    # Tests wrap_mode in (Modes.VERTICAL_HANGING_INDENT, Modes.VERTICAL_GRID_GROUPED) and comment lines[-1] processing (lines 118-138)
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    content = "a.b.c.d # comment"
    res = line(content, "\n", config)
    assert ")" in res




def test_line_content_empty_after_while_loop():
    # content becomes empty during while loop, falls back to content = next_line.pop() (line 104-105)
    config = Config(
        line_length=2,
        use_parentheses=True,
    )
    res = line("import a", "\n", config)
    assert res is not None


def test_line_splitter_starts_with_splitter():
    # line_without_comment.strip().startswith(splitter) is True -> skips splitter
    config = Config(
        line_length=5,
        use_parentheses=True,
    )
    # Starts directly with splitter, so re.search condition avoids it or falls through
    res = line("import a, b", "\n", config)
    assert res == "import a, b"
