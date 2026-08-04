# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

import pytest
from isort.parse import skip_line


def test_skip_line_already_in_quote():
    # Covers in_quote being initially truthy, and then closing the quote within the line.
    # line with closing quote
    skip, quote = skip_line('end_quote"', in_quote='"', index=0, section_comments=())
    assert skip is True
    assert quote == ""


def test_skip_line_escaped_character():
    # Covers line with backslash escaping inside or outside quotes
    skip, quote = skip_line(r'a = "hello\"world"', in_quote="", index=0, section_comments=())
    assert skip is False
    assert quote == ""


def test_skip_line_long_quotes():
    # Covers triple quotes (long_quote in ('"""', "'''"))
    skip, quote = skip_line('a = """hello', in_quote="", index=0, section_comments=())
    assert quote == '"""'


def test_skip_line_single_quote():
    # Covers single quote branch when not a long quote
    skip, quote = skip_line("a = 'hello", in_quote="", index=0, section_comments=())
    assert quote == "'"


def test_skip_line_comment_break():
    # Covers '#' breaking the while loop when not in a quote
    skip, quote = skip_line('x = 1 # comment with "quote"', in_quote="", index=0, section_comments=())
    assert skip is False
    assert quote == ""


def test_skip_line_semicolon_needs_import_various_parts():
    # Covers semicolon splitting, needs_import=True, and parts that trigger should_skip = True
    skip, quote = skip_line("import os; x = 1", in_quote="", index=0, section_comments=(), needs_import=True)
    assert skip is True

    # Covers semicolon part starting with 'from ' or 'import ' or empty (should not set should_skip)
    skip, quote = skip_line("import os; from a import b", in_quote="", index=0, section_comments=(), needs_import=True)
    assert skip is False

    skip, quote = skip_line("import os; import sys", in_quote="", index=0, section_comments=(), needs_import=True)
    assert skip is False

    skip, quote = skip_line("import os; cimport foo", in_quote="", index=0, section_comments=(), needs_import=True)
    assert skip is False

    # Covers needs_import=False preventing semicolon check
    skip, quote = skip_line("import os; x = 1", in_quote="", index=0, section_comments=(), needs_import=False)
    assert skip is False
