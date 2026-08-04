# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}

from isort.parse import skip_line

def test_skip_line_all_branches():
    # 1. in_quote is already True, and quote closing is encountered
    # Hits: line 95 (should_skip = True), line 96 (quote in line), line 101-103 (closing in_quote)
    skip, quote = skip_line(line='my_string" # comment', in_quote='"', index=0, section_comments=())
    assert skip is True
    assert quote == ""

    # 2. Escaped character inside quotes / general line
    # Hits: line 99-100 (backslash handling)
    skip, quote = skip_line(line=r'x = "abc\"def"', in_quote="", index=0, section_comments=())
    assert skip is False
    assert quote == ""

    # 3. Triple quotes opening and closing
    # Hits: line 105-108 (long_quote in ('"""', "'''"))
    skip, quote = skip_line(line='x = """hello', in_quote="", index=0, section_comments=())
    assert skip is True
    assert quote == '"""'

    # 4. Single quote opening (not triple quote)
    # Hits: line 110 (in_quote = line[char_index])
    skip, quote = skip_line(line="x = 'hello", in_quote="", index=0, section_comments=())
    assert skip is True
    assert quote == "'"

    # 5. Hash '#' comment encountered outside quotes, breaking the loop
    # Hits: line 111-112 (break on '#')
    skip, quote = skip_line(line="x = 1 # 'string inside comment'", in_quote="", index=0, section_comments=())
    assert skip is False
    assert quote == ""

    # 6. Semicolon line with valid import / needs_import False
    # Hits: line 115 (needs_import=False skips the semicolon checks)
    skip, quote = skip_line(line="import os; import sys", in_quote="", index=0, section_comments=(), needs_import=False)
    assert skip is False
    assert quote == ""

    # 7. Semicolon with non-import statement (e.g. assignment), needs_import=True
    # Hits: line 115-122 (should_skip = True due to semicolon part not being an import)
    skip, quote = skip_line(line="import os; x = 1", in_quote="", index=0, section_comments=(), needs_import=True)
    assert skip is True
    assert quote == ""

    # 8. Semicolon with empty parts or valid import parts
    # Hits: line 118-120 (part, not part.startswith("from "), not part.startswith(("import ", "cimport ")))
    skip, quote = skip_line(line="; import os; from y import z; cimport w", in_quote="", index=0, section_comments=(), needs_import=True)
    assert skip is False
    assert quote == ""
