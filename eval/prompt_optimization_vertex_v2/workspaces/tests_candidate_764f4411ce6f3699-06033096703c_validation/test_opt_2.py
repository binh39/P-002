# file: src\sample_repo\isort\isort\wrap.py:10-68
# asked: {"lines": [10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 23, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 45, 46, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 65, 66, 67, 68], "branches": [[20, 21], [20, 25], [42, 43], [42, 66], [45, 46], [45, 48], [50, 51], [50, 66], [66, 67], [66, 68]]}
# gained: {"lines": [10, 13, 14, 16, 17, 20, 21, 22, 23, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 45, 46, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 65, 66, 67, 68], "branches": [[20, 21], [20, 25], [42, 43], [42, 66], [45, 46], [45, 48], [50, 51], [50, 66], [66, 67], [66, 68]]}

import pytest
from isort.settings import Config
from isort.wrap import import_statement
from isort.wrap_modes import WrapModes


def test_import_statement_explode():
    # Covers explode=True branch (lines 20-23)
    res = import_statement("from module import", ["a", "b"], explode=True)
    assert isinstance(res, str)
    assert "a" in res
    assert "b" in res


def test_import_statement_multi_line_output_param():
    # Covers multi_line_output argument branch (line 25)
    config = Config(line_length=40)
    res = import_statement(
        "from module import",
        ["alpha", "beta", "gamma", "delta"],
        config=config,
        multi_line_output=WrapModes.VERTICAL_HANGING_INDENT,
    )
    assert isinstance(res, str)


def test_import_statement_balanced_wrapping():
    # Covers balanced_wrapping branches (lines 42-65)
    # Including len(lines) > 1 branch and len(lines) <= 1 branch (via multiple scenarios or config)
    config = Config(balanced_wrapping=True, line_length=40)
    res = import_statement(
        "from module import",
        ["alpha", "beta", "gamma", "delta", "epsilon"],
        config=config,
    )
    assert isinstance(res, str)


def test_import_statement_balanced_wrapping_single_line():
    # Forces len(lines) <= 1 when balanced_wrapping is True
    config = Config(balanced_wrapping=True, line_length=200)
    res = import_statement("from module import", ["alpha"], config=config)
    assert isinstance(res, str)


def test_import_statement_zero_separators():
    # Covers statement.count(line_separator) == 0 branch (lines 66-67)
    config = Config(line_length=200)
    res = import_statement("from module import", ["alpha"], config=config)
    assert isinstance(res, str)
