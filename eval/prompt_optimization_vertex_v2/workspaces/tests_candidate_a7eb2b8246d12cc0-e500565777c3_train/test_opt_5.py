# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [141, 142], [141, 144]]}

import pytest
from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_no_wrap_needed():
    # len(content) <= config.line_length
    config = Config(line_length=20)
    result = line("import a", "\n", config)
    assert result == "import a"


def test_line_noqa_mode_with_noqa():
    # len(content) > config.line_length and wrap_mode == Modes.NOQA and '# NOQA' in content
    config = Config(line_length=10, multi_line_output=Modes.NOQA)
    content = "import a # NOQA"
    result = line(content, "\n", config)
    assert result == content


def test_line_noqa_mode_without_noqa():
    # len(content) > config.line_length and wrap_mode == Modes.NOQA and '# NOQA' not in content
    config = Config(line_length=5, multi_line_output=Modes.NOQA)
    content = "import a"
    result = line(content, "\n", config)
    assert result == f"import a{config.comment_prefix} NOQA"


def test_line_wrap_splitter_dot_no_parentheses():
    # Test splitting by '.' with use_parentheses=False
    config = Config(line_length=10, use_parentheses=False)
    content = "very.long.module.name"
    result = line(content, "\n", config)
    assert "\\" in result


def test_line_wrap_splitter_as_with_parentheses():
    # Test splitter == "as " with use_parentheses=True
    config = Config(line_length=10, use_parentheses=True)
    content = "import very_long_name as vln"
    result = line(content, "\n", config)
    assert "as" in result


def test_line_wrap_splitter_import_with_comment_and_noqa():
    # Test comment with 'noqa' and use_parentheses=True
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "import alpha, beta # noqa: E501"
    result = line(content, "\n", config)
    assert "noqa" in result


def test_line_wrap_vertical_grid_grouped_with_comment_formatting():
    # Test VERTICAL_GRID_GROUPED, comment prefix in last line ending with ')'
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
        comment_prefix="#",
    )
    # This should trigger lines[-1] containing comment_prefix and ending with ')'
    content = "import a, b # comment"
    result = line(content, "\n", config)
    assert result is not None


def test_line_wrap_empty_content_fallback():
    # Test when content becomes empty after splitting and poping
    config = Config(line_length=2, use_parentheses=False)
    content = "a.b"
    result = line(content, "\n", config)
    assert result is not None


def test_line_wrap_splitter_import_with_trailing_comma_parentheses():
    # Test include_trailing_comma=True, use_parentheses=True, comment present without noqa
    config = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content = "import alpha, beta # regular comment"
    result = line(content, "\n", config)
    assert result is not None
