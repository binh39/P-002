# file: src\sample_repo\isort\isort\parse.py:53-63
# asked: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}
# gained: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}

import pytest
from isort.parse import import_type
from isort.settings import Config


def test_import_type_honor_noqa():
    # Test honor_noqa = True with line ending in noqa
    config_noqa = Config(honor_noqa=True)
    assert import_type("import os  # NOQA", config=config_noqa) is None
    assert import_type("from math import sqrt # noqa", config=config_noqa) is None

    # Test honor_noqa = False with line ending in noqa (should fall through)
    config_no_noqa = Config(honor_noqa=False)
    assert import_type("import os  # NOQA", config=config_no_noqa) == "straight"


def test_import_type_skips():
    # Test isort:skip
    assert import_type("import os  # isort:skip") is None
    # Test isort: skip
    assert import_type("import sys  # isort: skip") is None
    # Test isort: split
    assert import_type("import math  # isort: split") is None


def test_import_type_straight():
    # Test import starting with 'import '
    assert import_type("import os") == "straight"
    # Test import starting with 'cimport '
    assert import_type("cimport numpy as np") == "straight"


def test_import_type_from():
    # Test import starting with 'from '
    assert import_type("from os import path") == "from"


def test_import_type_none():
    # Test lines that don't match any import pattern
    assert import_type("x = 1") is None
    assert import_type("print('hello')") is None
    assert import_type("") is None
