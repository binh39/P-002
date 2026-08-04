# file: src\sample_repo\isort\isort\wrap.py:10-68
# asked: {"lines": [10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 23, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 45, 46, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 65, 66, 67, 68], "branches": [[20, 21], [20, 25], [42, 43], [42, 66], [45, 46], [45, 48], [50, 51], [50, 66], [66, 67], [66, 68]]}
# gained: {"lines": [10, 13, 14, 16, 17, 20, 21, 22, 23, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 45, 46, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 65, 66, 67, 68], "branches": [[20, 21], [20, 25], [42, 43], [42, 66], [45, 46], [45, 48], [50, 51], [50, 66], [66, 67], [66, 68]]}

import pytest
from isort.settings import Config
from isort.wrap import import_statement
from isort.wrap_modes import WrapModes


def test_import_statement_explode():
    # Test explode=True branch
    res = import_statement(
        "from module import",
        ["a", "b", "c"],
        explode=True,
    )
    assert "a" in res


def test_import_statement_multi_line_output_param():
    # Test multi_line_output parameter provided (branch: multi_line_output or config.multi_line_output)
    config = Config(line_length=80)
    res = import_statement(
        "from module import",
        ["alpha", "beta", "gamma", "delta", "epsilon"],
        config=config,
        multi_line_output=WrapModes.VERTICAL_HANGING_INDENT,
    )
    assert isinstance(res, str)


def test_import_statement_balanced_wrapping_single_line():
    # Test balanced_wrapping when len(lines) <= 1 (branch: else under if len(lines) > 1:)
    config = Config(balanced_wrapping=True, line_length=200)
    res = import_statement(
        "from module import",
        ["a"],
        config=config,
    )
    assert isinstance(res, str)


def test_import_statement_balanced_wrapping_multi_line_loop():
    # Test balanced_wrapping with multiple lines where the while loop runs and modifies line_length
    config = Config(balanced_wrapping=True, line_length=40)
    res = import_statement(
        "from very_long_module_name import",
        ["first_import", "second_import", "third_import", "fourth_import"],
        config=config,
        multi_line_output=WrapModes.VERTICAL_HANGING_INDENT,
    )
    assert isinstance(res, str)


def test_import_statement_no_newlines():
    # Test statement with no newlines (statement.count(line_separator) == 0) returning _wrap_line
    config = Config(line_length=200)
    res = import_statement(
        "import a",
        [],
        config=config,
    )
    assert isinstance(res, str)
