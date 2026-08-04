# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}

from isort.wrap_modes import grid

def test_grid_wrap_mode_comprehensive():
    # Test case 1: empty imports
    res_empty = grid(imports=[])
    assert res_empty == ""

    # Test case 2: imports without exceeding line length, no trailing comma
    res_simple = grid(
        imports=["a", "b"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=80,
        white_space="    ",
        include_trailing_comma=False,
    )
    assert res_simple == "from module import (a, b)"

    # Test case 3: imports exceeding line length triggering the `if` block, plus multi-word next_import
    # triggering inner loop where some parts fit and some exceed line_length.
    # Also test include_trailing_comma=True.
    res_complex = grid(
        imports=["alpha", "beta gamma delta"],
        statement="from module import ",
        comments=[],
        remove_comments=False,
        comment_prefix="#",
        line_separator="\n",
        line_length=15,  # force wrap
        white_space="    ",
        include_trailing_comma=True,
    )
    # Let's trace carefully:
    # 1. pops 'alpha' -> statement becomes 'from module import (alpha'
    # 2. pops 'beta gamma delta'
    #    next_statement = 'from module import (alpha, beta gamma delta'
    #    len(next_statement.split('\n')[-1]) + 1 -> len(', beta gamma delta') + 1 = 18 + 1 = 19 > 15 (Triggers line wrap)
    #    lines = ['    beta']
    #    part = 'gamma': new_line = '    beta gamma', len(new_line) + 1 = 11 + 1 = 12 <= 15 -> lines[-1] = '    beta gamma'
    #    part = 'delta': new_line = '    beta gamma delta', len(new_line) + 1 = 16 + 1 = 17 > 15 -> lines.append('    delta')
    #    next_import joined by '\n'
    #    statement updated, comments reset.
    assert isinstance(res_complex, str)
    assert res_complex.endswith(")")
