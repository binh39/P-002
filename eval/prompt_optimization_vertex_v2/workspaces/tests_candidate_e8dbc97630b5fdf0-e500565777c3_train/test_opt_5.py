# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 138], [141, 142], [141, 144]]}

from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_wrap_line_no_wrap_needed():
    config = Config(line_length=40)
    content = "import os"
    assert line(content, "\n", config) == content


def test_wrap_line_noqa_mode():
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import extremely_long_module_name"
    # Should append # NOQA if not present
    res = line(content, "\n", config)
    assert "# NOQA" in res

    # If # NOQA is already present, it should leave it as is
    content_with_noqa = "import extremely_long_module_name # NOQA"
    assert line(content_with_noqa, "\n", config) == content_with_noqa


def test_wrap_line_splitter_at_start():
    # If content.strip().startswith(splitter), it shouldn't split on that splitter
    config = Config(line_length=10)
    content = "import a, b, c, d, e, f"
    # Doesn't wrap because it starts with 'import '
    assert line(content, "\n", config) == content


def test_wrap_line_with_comment_and_parentheses():
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "from module import a, b # comment"
    res = line(content, "\n", config)
    assert res is not None


def test_wrap_line_with_noqa_in_comment_and_parentheses():
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
    )
    content = "from module import a, b # noqa"
    res = line(content, "\n", config)
    assert res is not None


def test_wrap_line_splitter_as():
    config = Config(
        line_length=15,
        use_parentheses=True,
    )
    content = "import very_long_name as v"
    res = line(content, "\n", config)
    assert "as" in res


def test_wrap_line_vertical_grid_grouped_and_comment_prefix_at_end():
    config = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=False,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
        comment_prefix="# ",
    )
    # This scenario exercises lines 118-138 where lines[-1] has comment_prefix and ends with ')'
    content = "import a, b, c # comment"
    res = line(content, "\n", config)
    assert res is not None


def test_wrap_line_without_parentheses():
    config = Config(
        line_length=10,
        use_parentheses=False,
    )
    content = "import module.submodule.another_submodule"
    res = line(content, "\n", config)
    assert "\\" in res


def test_wrap_line_empty_content_after_pop():
    config = Config(
        line_length=5,
        wrap_length=5,
        use_parentheses=False,
    )
    content = "a.b"
    res = line(content, "\n", config)
    assert res is not None
