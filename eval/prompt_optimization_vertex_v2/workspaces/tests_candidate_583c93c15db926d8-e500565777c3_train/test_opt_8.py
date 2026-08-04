# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 89, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 138], [141, 142], [141, 144]]}

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
    # len(content) > line_length and wrap_mode == Modes.NOQA and '# NOQA' not in content
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    res = line("import verylongname", "\n", config)
    assert res == f"import verylongname{config.comment_prefix} NOQA"


def test_line_noqa_mode_already_has_noqa():
    # len(content) > line_length and wrap_mode == Modes.NOQA and '# NOQA' in content (or uppercase check)
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import verylongname # NOQA"
    res = line(content, "\n", config)
    assert res == content


def test_line_splitter_at_start():
    # Matches splitter but starts with it, so search hits but not.strip().startswith()
    config = Config(line_length=10)
    # starts with 'import '
    content = "import a, b, c, d, e, f, g"
    res = line(content, "\n", config)
    # Should skip this splitter and eventually return content or handle via another splitter/branch
    assert res == content


def test_line_with_comment_and_use_parentheses_noqa():
    # comment and config.use_parentheses and "noqa" in comment
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "from module import a, b # noqa"
    res = line(content, "\n", config)
    assert "noqa" in res


def test_line_not_empty_content_after_while():
    # while loop pops line_parts, content becomes empty or non-empty
    config = Config(
        line_length=10,
        wrap_length=5,
        use_parentheses=False,
    )
    content = "from a import b"
    res = line(content, "\n", config)
    assert "\\" in res


def test_line_use_parentheses_splitter_as():
    # splitter == "as " with use_parentheses=True
    config = Config(
        line_length=10,
        use_parentheses=True,
    )
    content = "import a as very_long_alias_name"
    res = line(content, "\n", config)
    assert "as" in res


def test_line_use_parentheses_vertical_grid_grouped_and_comment_noqa():
    # wrap_mode in (Modes.VERTICAL_HANGING_INDENT, Modes.VERTICAL_GRID_GROUPED)
    # and comment and "noqa" in comment
    config = Config(
        line_length=10,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
        include_trailing_comma=True,
    )
    content = "from a import b # noqa"
    res = line(content, "\n", config)
    assert "noqa" in res


def test_line_use_parentheses_other_wrap_mode_no_comment():
    # wrap_mode NOT in (VERTICAL_HANGING_INDENT, VERTICAL_GRID_GROUPED), no comment
    config = Config(
        line_length=10,
        use_parentheses=True,
        multi_line_output=Modes.GRID,
        include_trailing_comma=True,
    )
    content = "from a import b, c, d"
    res = line(content, "\n", config)
    assert "(" in res


def test_line_comment_prefix_in_lines_last_and_ends_with_paren():
    # lines[-1] has comment_prefix and ends with ')'
    config = Config(
        line_length=10,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        include_trailing_comma=False,
    )
    content = "from a import b # comment"
    res = line(content, "\n", config)
    assert "#" in res
