# file: src\sample_repo\isort\isort\wrap.py:71-144
# asked: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 89, 90, 91, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 124, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 136, 137, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [118, 124], [126, 127], [126, 130], [135, 136], [135, 138], [141, 142], [141, 144]]}
# gained: {"lines": [71, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 89, 93, 95, 96, 98, 99, 100, 101, 102, 103, 104, 105, 107, 108, 109, 110, 112, 113, 114, 116, 118, 122, 125, 126, 127, 128, 129, 130, 131, 132, 134, 135, 138, 139, 140, 141, 142, 144], "branches": [[74, 75], [74, 141], [77, 78], [77, 79], [79, 80], [79, 144], [81, 79], [81, 84], [85, 86], [85, 98], [99, 102], [99, 104], [104, 105], [104, 107], [112, 113], [112, 140], [113, 114], [113, 116], [118, 122], [126, 127], [126, 130], [135, 138], [141, 142], [141, 144]]}

from isort.settings import Config
from isort.wrap import line
from isort.wrap_modes import WrapModes as Modes


def test_line_wrapping_comprehensive():
    # 1. Test len(content) <= line_length -> returns content directly (line 144)
    config = Config(line_length=40)
    res = line("import a", "\n", config)
    assert res == "import a"

    # 2. Test wrap_mode == Modes.NOQA with # NOQA in content (already has it) -> returns content
    config_noqa = Config(line_length=10, multi_line_output=Modes.NOQA)
    res = line("import long_module_name # NOQA", "\n", config_noqa)
    assert res == "import long_module_name # NOQA"

    # 3. Test wrap_mode == Modes.NOQA without # NOQA -> appends # NOQA (lines 141-142)
    res = line("import long_module_name", "\n", config_noqa)
    assert res == f"import long_module_name{config_noqa.comment_prefix} NOQA"

    # 4. Test splitting with a comment, use_parentheses=False, backslash wrapping (line 140)
    config_bs = Config(
        line_length=20,
        use_parentheses=False,
        multi_line_output=Modes.GRID,
    )
    res = line("from module import a, b # comment", "\n", config_bs)
    assert "\\" in res

    # 5. Test use_parentheses=True, splitter == "as " (lines 113-114)
    config_paren_as = Config(
        line_length=15,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    res = line("import x as very_long_alias", "\n", config_paren_as)
    assert "as" in res

    # 6. Test use_parentheses=True, splitter != "as ", wrap_mode in (VERTICAL_HANGING_INDENT, VERTICAL_GRID_GROUPED), include_trailing_comma=True, with comment containing noqa
    config_complex = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
        comment_prefix="#",
    )
    res = line("from mod import a, b, c # noqa", "\n", config_complex)
    assert "(" in res
    assert "noqa" in res

    # 7. Test VERTICAL_GRID_GROUPED to hit lines 118-122
    config_grid_grouped = Config(
        line_length=15,
        use_parentheses=True,
        include_trailing_comma=False,
        multi_line_output=Modes.VERTICAL_GRID_GROUPED,
    )
    res = line("from mod import a, b, c", "\n", config_grid_grouped)
    assert "(" in res

    # 8. Test when not content after pop in while loop (lines 104-105)
    config_pop = Config(
        line_length=5,
        use_parentheses=True,
        multi_line_output=Modes.VERTICAL_HANGING_INDENT,
    )
    res = line("from a import b", "\n", config_pop)
    assert "import" in res
