# file: src\sample_repo\isort\isort\parse.py:53-63
# asked: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}
# gained: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}

import pytest
from isort.settings import DEFAULT_CONFIG, Config
from isort.parse import import_type

# Test cases for the import_type function
def test_import_type_straight_import():
    line = "import os"
    result = import_type(line)
    assert result == "straight"

def test_import_type_cimport():
    line = "cimport numpy"
    result = import_type(line)
    assert result == "straight"

def test_import_type_from_import():
    line = "from datetime import datetime"
    result = import_type(line)
    assert result == "from"

def test_import_type_noqa():
    line = "import os  # noqa"
    config = Config(honor_noqa=True)
    result = import_type(line, config=config)
    assert result is None

def test_import_type_isort_skip():
    line = "isort: skip"
    result = import_type(line)
    assert result is None

def test_import_type_isort_split():
    line = "isort: split"
    result = import_type(line)
    assert result is None

def test_import_type_empty_string():
    line = ""
    result = import_type(line)
    assert result is None

def test_import_type_non_import_line():
    line = "print('Hello, World!')"
    result = import_type(line)
    assert result is None
