# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

import pytest
from isort.parse import skip_line


def test_skip_line_in_quote_continuation():
    # Test continuing within an already open quote, ending it
    skip, in_quote = skip_line('end_quote"', '"', 0, ())
    assert skip is True
    assert in_quote == ""


def test_skip_line_escaped_quote():
    # Test escaped backslash inside quote
    skip, in_quote = skip_line(r'some \" text', '"', 0, ())
    assert skip is True
    assert in_quote == '"'


def test_skip_line_triple_quotes():
    # Test opening and closing triple quotes (opening leaves in_quote set, so should_skip becomes True because bool(in_quote) is True)
    skip, in_quote = skip_line('"""docstring', "", 0, ())
    assert skip is True
    assert in_quote == '"""'

    # Close triple quote
    skip, in_quote = skip_line('end"""', '"""', 0, ())
    assert skip is True
    assert in_quote == ""


def test_skip_line_single_quote_and_comment():
    # Test opening single quote and hitting comment (#) after it
    skip, in_quote = skip_line("x = 'abc' # comment", "", 0, ())
    assert skip is False
    assert in_quote == ""


def test_skip_line_with_semicolon_non_import():
    # Test line with semicolon where a part is not an import statement
    skip, in_quote = skip_line("import os; x = 1", "", 0, (), needs_import=True)
    assert skip is True
    assert in_quote == ""


def test_skip_line_with_semicolon_all_imports():
    # Test line with semicolon where all parts are valid imports or empty
    skip, in_quote = skip_line("import os; import sys", "", 0, (), needs_import=True)
    assert skip is False
    assert in_quote == ""


def test_skip_line_with_semicolon_cimport():
    # Test cimport statement with semicolon
    skip, in_quote = skip_line("cimport foo; import bar", "", 0, (), needs_import=True)
    assert skip is False
    assert in_quote == ""


def test_skip_line_with_semicolon_from_import():
    # Test 'from ... import ...' statement with semicolon
    skip, in_quote = skip_line("from os import path; import sys", "", 0, (), needs_import=True)
    assert skip is False
    assert in_quote == ""


def test_skip_line_semicolon_no_needs_import():
    # Test semicolon when needs_import is False
    skip, in_quote = skip_line("import os; x = 1", "", 0, (), needs_import=False)
    assert skip is False
    assert in_quote == ""
