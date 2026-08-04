# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

from isort.parse import skip_line


def test_skip_line_in_quote_continuation():
    # Test when already in a quote and matching quote appears
    # in_quote = '"', line ends/closes the quote
    skip, quote = skip_line('some string"', '"', 0, ())
    assert skip is True
    assert quote == ""


def test_skip_line_backslash_escape():
    # Test backslash escape inside quotes or general line
    # '\\' skips the next character
    skip, quote = skip_line(r'\" quote', '"', 0, ())
    assert skip is True
    assert quote == '"'


def test_skip_line_triple_quotes():
    # Test entering and exiting triple quotes
    skip, quote = skip_line('"""docstring', "", 0, ())
    assert skip is True
    assert quote == '"""'

    # When a line closes triple quotes, in_quote becomes "" but since in_quote 
    # was truthy at the start of skip_line (should_skip = bool(in_quote)), 
    # or it is still considered part of a multi-line quote block being processed,
    # skip evaluates based on initial in_quote or final state.
    skip, quote = skip_line('end"""', '"""', 0, ())
    assert skip is True
    assert quote == ""


def test_skip_line_single_quote():
    # Test entering single quote
    skip, quote = skip_line("x = 'abc'", "", 0, ())
    assert skip is False
    assert quote == ""


def test_skip_line_comment_break():
    # Test encountering '#' outside quotes breaks the loop
    skip, quote = skip_line("x = 1 # comment '", "", 0, ())
    assert skip is False
    assert quote == ""


def test_skip_line_semicolon_needs_import():
    # Test semicolon parsing with needs_import=True
    # Part does not start with 'from ', 'import ', or 'cimport '
    skip, quote = skip_line("x = 1; y = 2", "", 0, (), needs_import=True)
    assert skip is True
    assert quote == ""

    # Part starts with 'import ' -> should not skip due to that part
    skip, quote = skip_line("import os; import sys", "", 0, (), needs_import=True)
    assert skip is False
    assert quote == ""


def test_skip_line_semicolon_no_needs_import():
    # Test semicolon parsing with needs_import=False
    skip, quote = skip_line("x = 1; y = 2", "", 0, (), needs_import=False)
    assert skip is False
    assert quote == ""
