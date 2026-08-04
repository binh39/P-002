# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 125, 126, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [126, 130], [135, 138], [141, 142], [141, 144]]}

from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_wrapping_comprehensive():
    # 1. Test line length <= config.line_length (returns content as is)
    cfg = Config(line_length=40)
    assert line("import os", "\n", cfg) == "import os"

    # 2. Test wrap_mode == Modes.NOQA and "# NOQA" not in content
    cfg_noqa = Config(line_length=10, multi_line_output=Modes.NOQA)
    res = line("import very_long_module_name", "\n", cfg_noqa)
    assert res == f"import very_long_module_name{cfg_noqa.comment_prefix} NOQA"

    # 3. Test wrap_mode == Modes.NOQA but "# NOQA" is already in content
    res2 = line("import very_long_module_name # NOQA", "\n", cfg_noqa)
    assert res2 == "import very_long_module_name # NOQA"

    # 4. Test splitters ("import ", "cimport ", ".", "as ") with comments, use_parentheses, noqa in comment, include_trailing_comma, etc.
    # Test splitter '.' with comment, use_parentheses=True, include_trailing_comma=True
    cfg_dot = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    # content has length > 15, contains '.', contains comment without 'noqa'
    res_dot = line("module.submodule # comment", "\n", cfg_dot)
    assert "module" in res_dot

    # Test splitter 'as ' with use_parentheses=True
    cfg_as = Config(
        line_length=10,
        use_parentheses=True,
        multi_line_output=Modes.GRID,
    )
    res_as = line("import a as b", "\n", cfg_as)
    assert "as" in res_as

    # Test splitter 'import ' with comment containing 'noqa', wrap_mode in VERTICAL_HANGING_INDENT
    cfg_noqa_comment = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    res_noqa_comm = line("import mod # noqa", "\n", cfg_noqa_comment)
    assert "noqa" in res_noqa_comm

    # Test splitter 'import ' without use_parentheses (backslash wrap) where line doesn't start with splitter
    cfg_noparen = Config(
        line_length=10,
        use_parentheses=False,
    )
    # Notice: line_without_comment.strip().startswith(splitter) must be False, so put something before 'import ' or use '.' / 'as ' / etc.
    res_noparen = line("from pkg import module_name", "\n", cfg_noparen)
    assert "\\" in res_noparen

    # Test when content becomes empty after while loop (not content -> content = next_line.pop())
    cfg_empty = Config(
        line_length=5,
        use_parentheses=False,
    )
    res_empty = line("from a import b", "\n", cfg_empty)
    assert res_empty is not None

    # Test lines[-1] having comment_prefix and ending with ')'
    cfg_comment_paren = Config(
        line_length=10,
        use_parentheses=True,
        include_trailing_comma=False,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    res_cp = line("os.path.join # comment", "\n", cfg_comment_paren)
    assert res_cp is not None
