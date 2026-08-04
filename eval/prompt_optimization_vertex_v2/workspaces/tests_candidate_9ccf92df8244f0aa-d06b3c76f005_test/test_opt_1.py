# file: src\sample_repo\isort\isort\wrap_modes.py:186-219
# asked: {"lines": [186, 187, 188, 190, 191, 192, 193, 194, 195, 197, 198, 199, 201, 202, 203, 204, 205, 207, 208, 210, 211, 212, 213, 214, 216, 217, 218, 219], "branches": [[187, 188], [187, 190], [201, 202], [201, 217], [205, 207], [205, 208], [208, 210], [208, 211], [211, 212], [211, 216], [217, 218], [217, 219]]}
# gained: {"lines": [186, 187, 188, 190, 191, 192, 193, 194, 195, 197, 198, 199, 201, 202, 203, 204, 205, 207, 208, 210, 211, 212, 213, 214, 216, 217, 218, 219], "branches": [[187, 188], [187, 190], [201, 202], [201, 217], [205, 207], [205, 208], [208, 210], [208, 211], [211, 212], [211, 216], [217, 218], [217, 219]]}

from isort.wrap_modes import _vertical_grid_common

def test_vertical_grid_common_empty_imports():
    result = _vertical_grid_common(
        need_trailing_char=False,
        imports=[],
        statement="from module import",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        indent="    ",
        include_trailing_comma=False,
        line_length=80,
    )
    assert result == ""

def test_vertical_grid_common_basic_wrapping():
    # Covers:
    # - non-empty imports
    # - while loop with multiple imports
    # - include_trailing_comma branch in length calculation
    # - not interface['imports'] and need_trailing_char branch
    # - current_line_length > interface['line_length'] triggering wrap
    # - include_trailing_comma at the end
    result = _vertical_grid_common(
        need_trailing_char=True,
        imports=["alpha", "beta", "gamma_very_long_import_name_to_force_wrap"],
        statement="from module import",
        comments=["# comment"],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        indent="    ",
        include_trailing_comma=True,
        line_length=30,
    )
    assert "alpha" in result
    assert "beta" in result
    assert result.endswith(",")

def test_vertical_grid_common_no_trailing_comma_no_need_trailing_char():
    # Covers when include_trailing_comma is False and need_trailing_char is False
    result = _vertical_grid_common(
        need_trailing_char=False,
        imports=["foo", "bar"],
        statement="import",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        indent="    ",
        include_trailing_comma=False,
        line_length=80,
    )
    assert "foo" in result
    assert "bar" in result
    assert not result.endswith(",")
