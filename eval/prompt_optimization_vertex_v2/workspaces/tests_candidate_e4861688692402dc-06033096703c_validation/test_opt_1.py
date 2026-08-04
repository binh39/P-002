# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

import pytest
from isort.parse import skip_line


def test_skip_line_in_quote_continuation():
    # Test when already in a quote and matching closing quote is found
    # Line starts inside a quote (in_quote = "'")
    skip, quote = skip_line("hello' world", "'", 0, (), True)
    assert skip is True
    assert quote == ""


def test_skip_line_escaped_character():
    # Test escaping inside quotes
    skip, quote = skip_line(r"\' world", "'", 0, (), True)
    # The backslash escapes the quote, so in_quote remains "'"
    assert quote == "'"


def test_skip_line_long_quote():
    # Test triple quotes starting
    skip, quote = skip_line('"""docstring', "", 0, (), True)
    assert quote == '"""'
    assert skip is True

    # Test single quote inside line
    skip, quote = skip_line('x = "hello"', "", 0, (), True)
    assert quote == ""
    assert skip is False


def test_skip_line_comment_break():
    # Test hitting a comment '#' outside quotes stops quote/char parsing
    skip, quote = skip_line("print(1) # '", "", 0, (), True)
    assert quote == ""
    assert skip is False


def test_skip_line_semicolon_statements():
    # Test semicolon with needs_import = True and non-import statements
    # e.g., "import os; x = 1"
    skip, quote = skip_line("import os; x = 1", "", 0, (), True)
    assert skip is True

    # Test semicolon with needs_import = False
    skip, quote = skip_line("import os; x = 1", "", 0, (), False)
    assert skip is False

    # Test semicolon with only valid import parts
    skip, quote = skip_line("import os; import sys", "", 0, (), True)
    assert skip is False

    # Test semicolon with 'from' part
    skip, quote = skip_line("import os; from math import pi", "", 0, (), True)
    assert skip is False

    # Test semicolon with 'cimport' part
    skip, quote = skip_line("import os; cimport c_mod", "", 0, (), True)
    assert skip is False

    # Test empty parts between semicolons
    skip, quote = skip_line("import os;; x = 1", "", 0, (), True)
    assert skip is True
