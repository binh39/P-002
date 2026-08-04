# file: src\sample_repo\isort\isort\parse.py:53-63
# asked: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}
# gained: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}

import pytest
from isort.parse import import_type
from isort.settings import DEFAULT_CONFIG, Config


def test_import_type_honor_noqa_true():
    config = Config(honor_noqa=True)
    assert import_type("import os # NOQA", config) is None
    assert import_type("from os import path  # noqa", config) is None


def test_import_type_honor_noqa_false():
    config = Config(honor_noqa=False)
    # Even with noqa, if honor_noqa is False, it should proceed to check import type
    assert import_type("import os # NOQA", config) == "straight"
    assert import_type("from os import path  # noqa", config) == "from"


def test_import_type_skip_comments():
    assert import_type("import os  # isort:skip", DEFAULT_CONFIG) is None
    assert import_type("import os  # isort: skip", DEFAULT_CONFIG) is None
    assert import_type("import os  # isort: split", DEFAULT_CONFIG) is None


def test_import_type_straight_imports():
    assert import_type("import os", DEFAULT_CONFIG) == "straight"
    assert import_type("cimport numpy", DEFAULT_CONFIG) == "straight"


def test_import_type_from_import():
    assert import_type("from os import path", DEFAULT_CONFIG) == "from"


def test_import_type_none():
    assert import_type("x = 1", DEFAULT_CONFIG) is None
