# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [126, 127], [126, 130], [135, 138], [141, 142], [141, 144]]}

from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_needed():
    # len(content) <= config.line_length
    content = "import os"
    res = line(content, "\n", Config(line_length=20))
    assert res == content


def test_line_noqa_mode_adds_noqa():
    # len(content) > config.line_length and wrap_mode == Modes.NOQA and "# NOQA" not in content
    content = "import a_very_long_module_name_that_exceeds_length"
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    res = line(content, "\n", config)
    assert res == f"import a_very_long_module_name_that_exceeds_length{config.comment_prefix} NOQA"


def test_line_noqa_mode_already_has_noqa():
    content = "import a_very_long_module_name_that_exceeds_length # NOQA"
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    res = line(content, "\n", config)
    assert res == content


def test_line_splitter_at_start():
    # line_without_comment.strip().startswith(splitter) -> True, should skip splitter
    content = "import a, b, c"
    config = Config(line_length=5, multi_line_output=Modes.GRID)
    res = line(content, "\n", config)
    assert res == content


def test_line_with_comment_and_use_parentheses_noqa():
    # comment and not (config.use_parentheses and "noqa" in comment) -> False
    content = "from module import a, b # noqa"
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    res = line(content, "\n", config)
    assert "noqa" in res


def test_line_with_comment_and_trailing_comma_handling():
    # config.include_trailing_comma and config.use_parentheses and not line_without_comment.rstrip().endswith(",")
    content = "from module import a, b # comment"
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    res = line(content, "\n", config)
    assert res is not None


def test_line_content_empty_after_while():
    # not content -> content = next_line.pop()
    content = "from a import b"
    config = Config(
        line_length=2,
        use_parentheses=False,
        multi_line_output=Modes.GRID,
    )
    res = line(content, "\n", config)
    assert res is not None


def test_line_splitter_is_as_with_parentheses():
    # splitter == "as " and config.use_parentheses
    content = "import long_module_name as lmn"
    config = Config(
        line_length=15,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    res = line(content, "\n", config)
    assert "as" in res


def test_line_vertical_grid_grouped_separator():
    # wrap_mode in (Modes.VERTICAL_HANGING_INDENT, Modes.VERTICAL_GRID_GROUPED)
    content = "from module import a, b, c, d"
    config = Config(
        line_length=10,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    res = line(content, "\n", config)
    assert res is not None


def test_line_comment_prefix_in_lines_last():
    # config.comment_prefix in lines[-1] and lines[-1].endswith(")")
    content = "from module import a # comment"
    config = Config(
        line_length=10,
        use_parentheses=True,
        comment_prefix="#",
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    res = line(content, "\n", config)
    assert res is not None


def test_line_without_parentheses():
    # not config.use_parentheses
    content = "from module import a, b, c, d"
    config = Config(
        line_length=10,
        use_parentheses=False,
        multi_line_output=Modes.GRID,
    )
    res = line(content, "\n", config)
    assert "\\" in res
