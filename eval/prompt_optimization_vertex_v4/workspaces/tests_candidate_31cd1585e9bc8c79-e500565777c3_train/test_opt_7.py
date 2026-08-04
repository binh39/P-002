# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 125, 126, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [126, 130], [135, 138], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_short_content():
    # len(content) <= line_length
    config = Config(line_length=50)
    res = line("import a", "\n", config)
    assert res == "import a"


def test_line_noqa_mode():
    # len(content) > line_length, wrap_mode == Modes.NOQA, '# NOQA' not in content
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    res = line("import very_long_module_name", "\n", config)
    assert res == f"import very_long_module_name{config.comment_prefix} NOQA"


def test_line_noqa_mode_already_has_noqa():
    # len(content) > line_length, wrap_mode == Modes.NOQA, but '# NOQA' in content
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    res = line("import very_long_module_name # NOQA", "\n", config)
    assert res == "import very_long_module_name # NOQA"


def test_line_wrap_with_splitter_and_comment():
    # Trigger splitter execution, comment present, use_parentheses = True, splitter = '.'
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "a.b.c.d.e # comment"
    res = line(content, "\n", config)
    assert "# comment" in res
    assert "(" in res


def test_line_wrap_splitter_as_and_no_parentheses():
    # use_parentheses = False, splitter = 'as '
    config = Config(
        line_length=15,
        use_parentheses=False,
    )
    content = "import long_mod as lm"
    res = line(content, "\n", config)
    assert "\\" in res


def test_line_wrap_splitter_as_with_parentheses():
    # use_parentheses = True, splitter = 'as '
    config = Config(
        line_length=15,
        use_parentheses=True,
    )
    content = "import long_mod as lm"
    res = line(content, "\n", config)
    assert "as" in res


def test_line_wrap_comment_with_noqa_and_parentheses():
    # comment with 'noqa' and use_parentheses = True
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "a.b.c.d # noqa"
    res = line(content, "\n", config)
    assert "noqa" in res


def test_line_wrap_empty_content_after_pop():
    # content becomes empty during while loop, falls back to next_line.pop()
    config = Config(
        line_length=5,
        use_parentheses=False,
        wrap_length=5,
    )
    content = "a.b"
    res = line(content, "\n", config)
    assert res is not None


def test_line_wrap_comment_ends_with_parenthesis_rearrangement():
    # Test lines[-1] containing comment_prefix and ending with ')'
    config = Config(
        line_length=10,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        comment_prefix="#",
    )
    # Construct input where the final wrapped part contains a comment and closes the paren
    content = "mod.submod # c"
    res = line(content, "\n", config)
    assert res is not None


def test_line_wrap_grid_grouped_mode():
    config = Config(
        line_length=10,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    content = "mod.submod.func"
    res = line(content, "\n", config)
    assert "\n" in res


def test_line_splitter_starts_with_splitter():
    # line_without_comment.strip().startswith(splitter) should be False for this branch to execute
    config = Config(line_length=10, use_parentheses=False)
    content = "some_module import something_long"
    res = line(content, "\n", config)
    assert res is not None
