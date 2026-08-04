# file: src\sample_repo\isort\isort\parse.py:53-63
# asked: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}
# gained: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}

import pytest
from isort.parse import import_type
from isort.settings import Config


def test_import_type_honor_noqa():
    config = Config(honor_noqa=True)
    # Test line ending with noqa (case-insensitive, trailing whitespace)
    assert import_type("import os # NOQA", config) is None
    assert import_type("import os  noqa  ", config) is None

    # Test when honor_noqa is False, it should proceed past this check
    config_no_noqa = Config(honor_noqa=False)
    assert import_type("import os # NOQA", config_no_noqa) == "straight"


def test_import_type_skips():
    assert import_type("import os # isort:skip") is None
    assert import_type("import os # isort: skip") is None
    assert import_type("import os # isort: split") is None


def test_import_type_straight():
    assert import_type("import os") == "straight"
    assert import_type("cimport module") == "straight"


def test_import_type_from():
    assert import_type("from os import path") == "from"


def test_import_type_none():
    assert import_type("x = 1") is None
    assert import_type("") is None
    assert import_type("importing = True") is None
