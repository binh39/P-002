# file: sample_repo\isort\isort\format.py:20-28
# asked: {"lines": [20, 21, 22, 23, 24, 25, 26, 28], "branches": [[22, 23], [22, 25], [25, 26], [25, 28]]}
# gained: {"lines": [20, 21, 22, 23, 24, 25, 26, 28], "branches": [[22, 23], [22, 25], [25, 26], [25, 28]]}

import pytest

from isort.format import format_simplified

def test_format_simplified_from_import():
    result = format_simplified("from module import function")
    assert result == "module.function"
    
def test_format_simplified_import():
    result = format_simplified("import module")
    assert result == "module"

def test_format_simplified_empty_string():
    result = format_simplified("")
    assert result == ""
