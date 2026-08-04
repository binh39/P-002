# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

from isort.parse import skip_line

def test_skip_line_all_branches():
    # 1. Line with backslash escaping inside quotes:
    # `in_quote` is already active, and there's an escaped quote inside.
    # Also tests when quote closes.
    skip, quote = skip_line(r'some text \" closing"', in_quote='"', index=0, section_comments=())
    assert skip is True
    assert quote == ""

    # 2. Long quote opening ('"""' or "'''") vs short quote (single character quote)
    # Testing triple quote opening
    skip, quote = skip_line('x = """hello', in_quote="", index=0, section_comments=())
    assert quote == '"""'

    # Testing single quote opening (else branch after checking long quote)
    skip, quote = skip_line("x = 'hello", in_quote="", index=0, section_comments=())
    assert quote == "'"

    # 3. Comment symbol '#' outside quotes stops parsing rest of line
    skip, quote = skip_line("a = 1 # 'unclosed quote", in_quote="", index=0, section_comments=())
    assert skip is False
    assert quote == ""

    # 4. Semicolon splitting tests when needs_import=True and needs_import=False
    # Part starts with 'from ' -> should not set should_skip via this part
    skip, quote = skip_line("from a import b; import c", in_quote="", index=0, section_comments=(), needs_import=True)
    assert skip is False

    # Part is empty or starts with 'import ' or 'cimport '
    skip, quote = skip_line("import a; cimport b;", in_quote="", index=0, section_comments=(), needs_import=True)
    assert skip is False

    # Part is a non-import statement separated by semicolon
    skip, quote = skip_line("import a; x = 1", in_quote="", index=0, section_comments=(), needs_import=True)
    assert skip is True

    # needs_import = False disables the semicolon check
    skip, quote = skip_line("import a; x = 1", in_quote="", index=0, section_comments=(), needs_import=False)
    assert skip is False

    # Semicolon inside comment should be ignored
    skip, quote = skip_line("import a # x = 1; y = 2", in_quote="", index=0, section_comments=(), needs_import=True)
    assert skip is False
