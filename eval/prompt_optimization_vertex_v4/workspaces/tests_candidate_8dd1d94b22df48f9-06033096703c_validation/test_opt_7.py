# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

from isort.parse import skip_line


def test_skip_line_basic_in_quote():
    # Test when already in_quote and closing quote is reached
    res = skip_line('some text"', '"', 0, ())
    assert res == (True, "")


def test_skip_line_escaped_character():
    # Test backslash escape inside quote where quote is not closed
    res = skip_line(r'some \" text', '"', 0, ())
    assert res == (True, '"')


def test_skip_line_triple_quote():
    # Test triple quote start and long quote matching
    res = skip_line('""" hello', "", 0, ())
    assert res == (True, '"""')


def test_skip_line_single_quote_inside():
    # Test single quote start and break on '#'
    res = skip_line("x = 'abc' # comment", "", 0, ())
    assert res == (False, "")


def test_skip_line_semicolon_needs_import():
    # Test semicolon parsing with needs_import=True, where a part is not an import/from
    res = skip_line("x = 1; y = 2", "", 0, (), needs_import=True)
    assert res == (True, "")


def test_skip_line_semicolon_with_import_and_comment():
    # Test semicolon parsing where parts are valid imports/from statements
    res = skip_line("import os; from sys import path", "", 0, (), needs_import=True)
    assert res == (False, "")


def test_skip_line_semicolon_needs_import_false():
    # Test semicolon parsing when needs_import is False
    res = skip_line("x = 1; y = 2", "", 0, (), needs_import=False)
    assert res == (False, "")
