# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

import pytest
from isort.parse import skip_line


def test_skip_line_already_in_quote():
    # Test when already in quote, and the quote closes within the line
    # Covers: in_quote is truthy, matching quote found, resetting in_quote = ''
    skip, quote = skip_line(line='to_close"', in_quote='"', index=0, section_comments=())
    assert skip is True
    assert quote == ""


def test_skip_line_escaped_character_in_quote():
    # Test escape character handling inside quotes (backslash skips next char)
    # Covers: line[char_index] == '\\', char_index += 1
    skip, quote = skip_line(line=r'esc\"aped"', in_quote='"', index=0, section_comments=())
    assert skip is True
    assert quote == ""


def test_skip_line_triple_quotes():
    # Test triple quote start and long_quote in ('"""', "'''") branch
    # Covers: long_quote in ('"""', "'''"), char_index += 2
    skip, quote = skip_line(line='x = """abc', in_quote="", index=0, section_comments=())
    assert skip is True
    assert quote == '"""'


def test_skip_line_single_quote():
    # Test single quote start (not triple quote) else branch
    # Covers: else block for single quote
    skip, quote = skip_line(line="x = 'abc", in_quote="", index=0, section_comments=())
    assert skip is True
    assert quote == "'"


def test_skip_line_comment_char_stops_parsing():
    # Test '#' character breaking out of the quote/char loop
    # Covers: line[char_index] == '#' -> break
    skip, quote = skip_line(line='a = 1 # "quote inside comment', in_quote="", index=0, section_comments=())
    assert skip is False
    assert quote == ""


def test_skip_line_semicolon_needs_import_true_non_import():
    # Test semicolons with needs_import=True where statements are not imports/from
    # Covers: ';' in line.split('#')[0] and needs_import, part not startswith 'from ' or 'import '/'cimport ' -> should_skip = True
    skip, quote = skip_line(line="x = 1; y = 2", in_quote="", index=0, section_comments=(), needs_import=True)
    assert skip is True
    assert quote == ""


def test_skip_line_semicolon_needs_import_false():
    # Test semicolons when needs_import=False (should not skip even if non-import statements exist)
    # Covers: needs_import=False branch
    skip, quote = skip_line(line="x = 1; y = 2", in_quote="", index=0, section_comments=(), needs_import=False)
    assert skip is False
    assert quote == ""


def test_skip_line_semicolon_with_import_part():
    # Test semicolon containing valid import parts alongside non-import parts
    # Covers: part.startswith("import ") or part.startswith("from ") being False for some parts but True for others or handled properly
    skip, quote = skip_line(line="import os; x = 1", in_quote="", index=0, section_comments=(), needs_import=True)
    assert skip is True
    assert quote == ""
