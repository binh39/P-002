# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

from isort.parse import skip_line

def test_skip_line_all_branches():
    # 1. in_quote is initially non-empty, and closing quote is reached
    # Exercises: should_skip = True (from bool(in_quote)), elif in_quote branch, quote closing.
    skip, quote = skip_line('some text """', '"""', 0, (), True)
    assert skip is True
    assert quote == ""

    # 2. Line with escaped quotes inside quote or outside quote
    # Exercises: line[char_index] == '\\'
    skip, quote = skip_line(r'\" text', '"', 0, (), True)
    assert skip is True
    assert quote == '"'

    # 3. Triple quote opening (long_quote in ('"""', "'''"))
    # Exercises: long_quote in ('"""', "'''"), char_index += 2
    skip, quote = skip_line('x = """abc', '', 0, (), True)
    assert skip is True
    assert quote == '"""'

    # 4. Single quote opening (else branch after long quote check)
    # Exercises: else: in_quote = line[char_index]
    skip, quote = skip_line("x = 'abc", "", 0, (), True)
    assert skip is True
    assert quote == "'"

    # 5. Hash character outside quotes breaks the character loop
    # Exercises: elif line[char_index] == "#": break
    skip, quote = skip_line("x = 1 # 'comment'", "", 0, (), True)
    assert skip is False
    assert quote == ""

    # 6. Semicolon line without import/from/cimport and needs_import=True
    # Exercises: ';' in line.split('#')[0] and needs_import, part not starting with 'from ', 'import ', 'cimport ' -> should_skip = True
    skip, quote = skip_line("x = 1; y = 2", "", 0, (), True)
    assert skip is True
    assert quote == ""

    # 7. Semicolon line with valid import and needs_import=True
    # Exercises: part starting with 'import ' or 'from ' or empty part, so should_skip remains False
    skip, quote = skip_line("import a; import b", "", 0, (), True)
    assert skip is False
    assert quote == ""

    # 8. Semicolon line but needs_import=False
    # Exercises: needs_import is False so semicolon check is skipped
    skip, quote = skip_line("x = 1; y = 2", "", 0, (), False)
    assert skip is False
    assert quote == ""
