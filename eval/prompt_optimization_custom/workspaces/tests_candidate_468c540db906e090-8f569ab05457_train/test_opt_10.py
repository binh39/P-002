# file: src\sample_repo\isort\isort\parse.py:53-63
# asked: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}
# gained: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}

import pytest
from isort.settings import DEFAULT_CONFIG, Config
from isort.parse import import_type

# Test cases for the import_type function

def test_import_type_with_noqa():
    line = "import something  # noqa"
    config = Config(honor_noqa=True)
    result = import_type(line, config)
    assert result is None, "Expected None for line ending with 'noqa'"

def test_import_type_with_isort_skip():
    line = "isort: skip"
    result = import_type(line)
    assert result is None, "Expected None for line containing 'isort: skip'"

def test_import_type_with_isort_split():
    line = "isort: split"
    result = import_type(line)
    assert result is None, "Expected None for line containing 'isort: split'"

def test_import_type_straight_import():
    line = "import os"
    result = import_type(line)
    assert result == "straight", "Expected 'straight' for a standard import"

def test_import_type_from_import():
    line = "from os import path"
    result = import_type(line)
    assert result == "from", "Expected 'from' for a from-import statement"

def test_import_type_empty_line():
    line = ""
    result = import_type(line)
    assert result is None, "Expected None for an empty line"
