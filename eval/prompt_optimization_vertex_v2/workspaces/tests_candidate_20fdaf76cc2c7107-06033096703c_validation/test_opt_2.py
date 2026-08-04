# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

import pytest
from isort.parse import skip_line


def test_skip_line_already_in_quote_and_closes():
    # Test when already inside a quote, and the closing quote is encountered on the line
    line = 'some text"'
    in_quote = '"'
    skip, new_quote = skip_line(line, in_quote, 0, (), needs_import=True)
    assert skip is True
    assert new_quote == ""


def test_skip_line_already_in_quote_remains_open():
    # Test when inside a quote, but quote does not close
    line = 'some text'
    in_quote = '"'
    skip, new_quote = skip_line(line, in_quote, 0, (), needs_import=True)
    assert skip is True
    assert new_quote == '"'


def test_skip_line_escaped_character_inside_quote():
    # Test handling of escaped characters (backslash) within quotes
    line = r'text \"quote"'
    in_quote = '"'
    skip, new_quote = skip_line(line, in_quote, 0, (), needs_import=True)
    assert skip is True
    assert new_quote == ""


def test_skip_line_triple_quote_start():
    # Test starting a triple quote block
    line = 'x = """hello'
    in_quote = ""
    skip, new_quote = skip_line(line, in_quote, 0, (), needs_import=True)
    assert skip is True
    assert new_quote == '"""'


def test_skip_line_single_quote_start():
    # Test starting a single quote block
    line = "x = 'hello"
    in_quote = ""
    skip, new_quote = skip_line(line, in_quote, 0, (), needs_import=True)
    assert skip is True
    assert new_quote == "'"


def test_skip_line_comment_halts_quote_search():
    # Test that a comment character # stops further quote parsing on the line
    line = "x = 1 # 'comment"
    in_quote = ""
    skip, new_quote = skip_line(line, in_quote, 0, (), needs_import=True)
    assert skip is False
    assert new_quote == ""


def test_skip_line_semicolon_non_import_part():
    # Test semicolon separating multiple statements where one is not an import/from-import
    line = "import os; x = 1"
    in_quote = ""
    skip, new_quote = skip_line(line, in_quote, 0, (), needs_import=True)
    assert skip is True
    assert new_quote == ""


def test_skip_line_semicolon_valid_imports():
    # Test semicolon separating statements that are valid imports/cimports
    line = "import os; import sys"
    in_quote = ""
    skip, new_quote = skip_line(line, in_quote, 0, (), needs_import=True)
    assert skip is False
    assert new_quote == ""


def test_skip_line_semicolon_needs_import_false():
    # Test semicolon parsing when needs_import is False
    line = "import os; x = 1"
    in_quote = ""
    skip, new_quote = skip_line(line, in_quote, 0, (), needs_import=False)
    assert skip is False
    assert new_quote == ""


def test_skip_line_semicolon_with_comment_ignoring_semicolon_in_comment():
    # Test semicolon inside a comment after a valid import
    line = "import os # comment; x = 1"
    in_quote = ""
    skip, new_quote = skip_line(line, in_quote, 0, (), needs_import=True)
    assert skip is False
    assert new_quote == ""


def test_skip_line_cimport_semicolon():
    # Test semicolon with cimport statement
    line = "cimport module; import sys"
    in_quote = ""
    skip, new_quote = skip_line(line, in_quote, 0, (), needs_import=True)
    assert skip is False
    assert new_quote == ""
