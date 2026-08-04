# file: src\sample_repo\isort\isort\parse.py:53-63
# asked: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}
# gained: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}

import pytest
from isort.parse import import_type
from isort.settings import Config


def test_import_type_honor_noqa():
    config = Config(honor_noqa=True)
    # Line ends with noqa (case-insensitive, with trailing spaces)
    assert import_type("import os  # NOQA", config) is None
    assert import_type("import sys  # noqa", config) is None

    # Without honor_noqa, it should be recognized as straight import
    config_no_noqa = Config(honor_noqa=False)
    assert import_type("import os  # noqa", config_no_noqa) == "straight"


def test_import_type_skips():
    assert import_type("import os # isort:skip") is None
    assert import_type("import os # isort: skip") is None
    assert import_type("import os # isort: split") is None


def test_import_type_straight_imports():
    assert import_type("import os") == "straight"
    assert import_type("cimport numpy") == "straight"


def test_import_type_from_imports():
    assert import_type("from os import path") == "from"


def test_import_type_none():
    assert import_type("print('hello')") is None
    assert import_type("") is None
