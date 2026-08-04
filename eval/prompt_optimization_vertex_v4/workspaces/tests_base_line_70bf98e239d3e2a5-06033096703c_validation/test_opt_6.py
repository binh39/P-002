# file: src\sample_repo\isort\isort\parse.py:81-124
# asked: {"lines": [81, 82, 83, 84, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 112, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 112], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 116], [117, 122]]}
# gained: {"lines": [81, 85, 86, 87, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 110, 111, 113, 115, 116, 118, 119, 120, 122, 124], "branches": [[96, 97], [96, 115], [98, 99], [98, 115], [99, 100], [99, 101], [101, 102], [101, 104], [102, 103], [102, 113], [104, 105], [104, 111], [106, 107], [106, 110], [111, 113], [115, 116], [115, 124], [116, 117], [116, 124], [117, 122]]}

from isort.parse import skip_line

def test_skip_line_all_branches():
    # 1. in_quote initially non-empty, encounters closing quote with escape and inner chars
    res, quote = skip_line(r'foo\"bar', '"""', 0, (), needs_import=True)
    assert quote == '"""'
    assert res is True

    # Properly close a triple quote with escape handling
    line_close = r'a\"""b'
    res, quote = skip_line(line_close, '"""', 0, (), needs_import=True)
    assert quote == '"""'

    res, quote = skip_line(r'foo\"bar', '"', 0, (), needs_import=True)
    assert quote == '"'

    # Close single quote normally
    res, quote = skip_line('bar"', '"', 0, (), needs_import=True)
    assert quote == ''
    assert res is True

    # 2. Opening single quote vs triple quote (long_quote in ('"""', "'''"))
    res, quote = skip_line('x = """hello', '', 0, (), needs_import=True)
    assert quote == '"""'
    assert res is True

    res, quote = skip_line("x = 'hello", '', 0, (), needs_import=True)
    assert quote == "'"
    assert res is True

    res, quote = skip_line('x = "hello', '', 0, (), needs_import=True)
    assert quote == '"'
    assert res is True

    # Test hitting comment character '#' inside line when not in quote
    res, quote = skip_line('x = 1 # comment', '', 0, (), needs_import=True)
    assert quote == ''
    assert res is False

    # 3. Semicolon splitting and needs_import checks (lines 115-122)
    # A statement with a semicolon where a part doesn't start with from/import/cimport sets should_skip = True
    res, quote = skip_line('a = 1; x = 2', '', 0, (), needs_import=True)
    assert res is True

    # Even if one part is "from b import c", if there is ANOTHER part that is NOT an import/from/cimport (like "a = 1"),
    # should_skip becomes True because `any` part triggers it across the loop.
    # To test parts that DO NOT trigger should_skip, every part must be an import or empty.
    res, quote = skip_line('from b import c', '', 0, (), needs_import=True)
    assert res is False

    res, quote = skip_line('import b', '', 0, (), needs_import=True)
    assert res is False

    res, quote = skip_line('cimport b', '', 0, (), needs_import=True)
    assert res is False

    # needs_import = False (should NOT trigger semicolon check)
    res, quote = skip_line('a = 1; x = 2', '', 0, (), needs_import=False)
    assert res is False

    # Semicolon inside a comment part should be ignored by split('#')[0]
    res, quote = skip_line('a = 1 # comment; with semicolon', '', 0, (), needs_import=True)
    assert res is False
