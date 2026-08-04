# file: src\sample_repo\isort\isort\wrap.py:10-68
# asked: {"lines": [10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 23, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 45, 46, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 65, 66, 67, 68], "branches": [[20, 21], [20, 25], [42, 43], [42, 66], [45, 46], [45, 48], [50, 51], [50, 66], [66, 67], [66, 68]]}
# gained: {"lines": [10, 13, 14, 16, 17, 20, 21, 22, 23, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 45, 46, 48, 49, 50, 66, 67, 68], "branches": [[20, 21], [20, 25], [42, 43], [42, 66], [45, 46], [45, 48], [50, 66], [66, 67], [66, 68]]}

import pytest
from isort.settings import Config
from isort.wrap import import_statement
from isort.wrap_modes import WrapModes


def test_import_statement_explode():
    result = import_statement(
        import_start="from module import",
        from_imports=["a", "b"],
        explode=True,
    )
    assert "a" in result
    assert "b" in result


def test_import_statement_multi_line_output_param():
    config = Config(line_length=80)
    result = import_statement(
        import_start="from module import",
        from_imports=["long_import_name_a", "long_import_name_b"],
        multi_line_output=WrapModes.VERTICAL_HANGING_INDENT,
        config=config,
    )
    assert result is not None


def test_import_statement_balanced_wrapping_single_line():
    config = Config(balanced_wrapping=True, line_length=120)
    result = import_statement(
        import_start="from module import",
        from_imports=["a"],
        config=config,
    )
    assert result is not None


def test_import_statement_balanced_wrapping_multi_line():
    config = Config(balanced_wrapping=True, line_length=20)
    result = import_statement(
        import_start="from module import",
        from_imports=["foo", "bar", "baz"],
        config=config,
    )
    assert result is not None


def test_import_statement_no_newline():
    config = Config(line_length=200)
    result = import_statement(
        import_start="from module import",
        from_imports=["a"],
        line_separator="\n",
        config=config,
    )
    assert result is not None
