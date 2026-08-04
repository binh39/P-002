# file: src\sample_repo\isort\isort\wrap_modes.py:186-219
# asked: {"lines": [186, 187, 188, 190, 191, 192, 193, 194, 195, 197, 198, 199, 201, 202, 203, 204, 205, 207, 208, 210, 211, 212, 213, 214, 216, 217, 218, 219], "branches": [[187, 188], [187, 190], [201, 202], [201, 217], [205, 207], [205, 208], [208, 210], [208, 211], [211, 212], [211, 216], [217, 218], [217, 219]]}
# gained: {"lines": [186, 187, 188, 190, 191, 192, 193, 194, 195, 197, 198, 199, 201, 202, 203, 204, 205, 207, 208, 210, 211, 212, 213, 214, 216, 217, 218, 219], "branches": [[187, 188], [187, 190], [201, 202], [201, 217], [205, 207], [208, 210], [208, 211], [211, 212], [211, 216], [217, 218]]}

from isort.wrap_modes import _vertical_grid_common

def test_vertical_grid_common_empty_imports():
    result = _vertical_grid_common(
        True,
        imports=[],
        statement="",
        comments=[],
        remove_comments=[],
        comment_prefix="#",
        line_separator="\n",
        indent="    ",
        include_trailing_comma=False,
        line_length=80,
    )
    assert result == ""

def test_vertical_grid_common_basic_wrapping_and_branches():
    # This test triggers:
    # - non-empty imports
    # - while loop over multiple imports
    # - branch where interface["imports"] is truthy / include_trailing_comma is False/True
    # - branch where not interface["imports"] and need_trailing_char
    # - line length exceeded triggering wrapping inside the while loop
    # - include_trailing_comma at the end
    result = _vertical_grid_common(
        need_trailing_char=True,
        imports=["import_a", "import_b", "import_c"],
        statement="from module import ",
        comments=[],
        remove_comments=[],
        comment_prefix="#",
        line_separator="\n",
        indent="    ",
        include_trailing_comma=True,
        line_length=25,
    )
    assert isinstance(result, str)
    assert "import_a" in result
    assert "import_b" in result
    assert "import_c" in result
