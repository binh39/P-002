# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

from isort.parse import skip_line


def test_skip_line_basic_and_quotes():
    # 1. Already in quote, closing quote found
    # Line starts inside a double quote, encounters closing quote
    assert skip_line(line='hello"', in_quote='"', index=0, section_comments=()) == (True, "")

    # 2. Backslash escape inside quotes
    assert skip_line(line=r'he\"llo"', in_quote='"', index=0, section_comments=()) == (True, "")

    # 3. Opening long quote (""")
    assert skip_line(line='"""hello', in_quote="", index=0, section_comments=()) == (True, '"""')

    # 4. Opening short quote (')
    assert skip_line(line="x = 'hello'", in_quote="", index=0, section_comments=()) == (False, "")

    # 5. Comment character encountered outside quotes (#)
    assert skip_line(line="x = 1 # comment", in_quote="", index=0, section_comments=()) == (False, "")


def test_skip_line_semicolon_and_needs_import():
    # Semicolon present, needs_import=True, non-import part exists ("a = 1") -> should_skip = True
    assert skip_line(
        line="a = 1; import os",
        in_quote="",
        index=0,
        section_comments=(),
        needs_import=True,
    ) == (True, "")

    # Semicolon present, but all parts are valid import statements -> should_skip remains False
    assert skip_line(
        line="import sys; import os",
        in_quote="",
        index=0,
        section_comments=(),
        needs_import=True,
    ) == (False, "")

    # Semicolon present, but needs_import=False -> should_skip remains False
    assert skip_line(
        line="a = 1; b = 2",
        in_quote="",
        index=0,
        section_comments=(),
        needs_import=False,
    ) == (False, "")

    # Semicolon after a comment character (split('#')[0] handles this)
    assert skip_line(
        line="import os # comment with ; inside",
        in_quote="",
        index=0,
        section_comments=(),
        needs_import=True,
    ) == (False, "")
