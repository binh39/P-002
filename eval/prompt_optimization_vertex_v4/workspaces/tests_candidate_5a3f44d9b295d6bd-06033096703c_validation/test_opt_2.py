# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

from isort.parse import skip_line


def test_skip_line_already_in_quote_and_closing():
    # Test starting inside a quote and closing it
    # in_quote = '"', line = 'foo" bar'
    skip, new_quote = skip_line('foo" bar', '"', 0, ())
    assert skip is True
    assert new_quote == ""


def test_skip_line_escaped_quote():
    # Test escaped quote and escaped backslash
    # in_quote = '"', line = r'foo\" bar\\'
    skip, new_quote = skip_line(r'foo\" bar\\', '"', 0, ())
    assert skip is True
    assert new_quote == '"'


def test_skip_line_triple_quotes():
    # Test opening and closing triple quotes, and single quotes
    skip, new_quote = skip_line('x = """hello"""', "", 0, ())
    assert skip is False
    assert new_quote == ""

    # Open triple quote without closing on same line
    skip, new_quote = skip_line('x = """hello', "", 0, ())
    assert skip is True
    assert new_quote == '"""'

    # Single quote open/close
    skip, new_quote = skip_line("x = 'hello'", "", 0, ())
    assert skip is False
    assert new_quote == ""

    # Single quote open without close
    skip, new_quote = skip_line("x = 'hello", "", 0, ())
    assert skip is True
    assert new_quote == "'"


def test_skip_line_comment_breaks_quote_parsing():
    # '#' encountered before quote parsing finishes or starts
    skip, new_quote = skip_line("print(1) # 'hello", "", 0, ())
    assert skip is False
    assert new_quote == ""


def test_skip_line_semicolon_needs_import_variants():
    # Semicolon with non-import statement (should skip)
    skip, new_quote = skip_line("x = 1; y = 2", "", 0, ())
    assert skip is True
    assert new_quote == ""

    # Semicolon with valid 'from' or 'import' statements (should not skip due to semicolon check)
    skip, new_quote = skip_line("import os; import sys", "", 0, ())
    assert skip is False
    assert new_quote == ""

    skip, new_quote = skip_line("from os import path; import sys", "", 0, ())
    assert skip is False
    assert new_quote == ""

    skip, new_quote = skip_line("cimport foo; import bar", "", 0, ())
    assert skip is False
    assert new_quote == ""

    # Semicolon with needs_import = False (should not skip)
    skip, new_quote = skip_line("x = 1; y = 2", "", 0, (), needs_import=False)
    assert skip is False
    assert new_quote == ""

    # Semicolon inside a comment part (split('#')[0] ignores semicolon after #)
    skip, new_quote = skip_line("import os # x = 1; y = 2", "", 0, ())
    assert skip is False
    assert new_quote == ""
