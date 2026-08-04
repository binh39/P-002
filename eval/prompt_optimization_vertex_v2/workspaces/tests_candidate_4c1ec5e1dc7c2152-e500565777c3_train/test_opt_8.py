# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 98], [99, 102], [99, 104], [104, 105], [112, 113], [112, 140], [113, 114], [141, 142], [141, 144]]}

from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_wrap_line_comprehensive_coverage():
    # 1. Test line length <= config.line_length (returns content as-is)
    cfg = Config(line_length=40)
    assert line("short content", "\n", cfg) == "short content"

    # 2. Test wrap_mode == Modes.NOQA with # NOQA present (returns content as-is)
    long_noqa = "from a.b.c.d.e.f.g import h # NOQA"
    cfg_noqa = Config(line_length=20, multi_line_output=Modes.NOQA)
    assert line(long_noqa, "\n", cfg_noqa) == long_noqa

    # 3. Test wrap_mode == Modes.NOQA without # NOQA present (appends # NOQA using comment_prefix)
    long_noqa_missing = "from a.b.c.d.e.f.g import h"
    res_noqa = line(long_noqa_missing, "\n", cfg_noqa)
    assert "NOQA" in res_noqa

    # 4. Test splitting with comment, use_parentheses=True, include_trailing_comma=True, comment has 'noqa'
    # Hits: comment with noqa, include_trailing_comma, wrap_mode vertical hanging or grid grouped,
    # and lines[-1] ending with ')' containing comment prefix.
    cfg_parentheses_noqa = Config(
        line_length=30,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        comment_prefix="#",
    )
    content_with_noqa = "import alpha, beta, gamma # noqa: E501"
    res = line(content_with_noqa, "\n", cfg_parentheses_noqa)
    assert isinstance(res, str)
    assert "noqa" in res

    # 5. Test use_parentheses=True and splitter == "as "
    cfg_as = Config(
        line_length=10,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    content_as = "import really_long_name as r"
    res_as = line(content_as, "\n", cfg_as)
    assert "as" in res_as

    # 6. Test use_parentheses=True with wrap_mode NOT in VERTICAL_HANGING_INDENT or VERTICAL_GRID_GROUPED (e.g. modes that set _separator = "")
    cfg_grid = Config(
        line_length=15,
        use_parentheses=True,
        multi_line_output=Modes.GRID,
    )
    content_grid = "import alpha, beta, gamma"
    res_grid = line(content_grid, "\n", cfg_grid)
    assert isinstance(res_grid, str)

    # 7. Test use_parentheses=False (falls back to backslash line continuation when line is actually wrapped)
    cfg_backslash = Config(
        line_length=10,
        use_parentheses=False,
    )
    content_bs = "import alpha, beta, gamma"
    res_bs = line(content_bs, "\n", cfg_backslash)
    assert isinstance(res_bs, str)

    # 8. Test comment present without 'noqa', include_trailing_comma=True, use_parentheses=True
    cfg_comment_commas = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    content_commas = "import foo, bar # my comment"
    res_commas = line(content_commas, "\n", cfg_comment_commas)
    assert "my comment" in res_commas

    # 9. Test content empty after while loop (if not content: content = next_line.pop())
    cfg_empty_content = Config(
        line_length=2,
        use_parentheses=False,
    )
    content_short_parts = "a.b"
    res_empty = line(content_short_parts, "\n", cfg_empty_content)
    assert isinstance(res_empty, str)
