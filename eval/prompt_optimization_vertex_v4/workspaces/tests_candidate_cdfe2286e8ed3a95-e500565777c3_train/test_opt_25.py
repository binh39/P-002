# file: src\sample_repo\isort\isort\parse.py:53-63
# asked: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}
# gained: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}

import pytest
from isort.parse import import_type
from isort.settings import DEFAULT_CONFIG, Config


def test_import_type_honor_noqa_true():
    config = Config(honor_noqa=True)
    assert import_type("import os  # NOQA", config) is None
    assert import_type("from os import path  # noqa", config) is None


def test_import_type_honor_noqa_false():
    config = Config(honor_noqa=False)
    # When honor_noqa is False, a line ending in noqa should not return None immediately
    assert import_type("import os  # noqa", config) == "straight"


def test_import_type_skip_comments():
    assert import_type("import os  # isort:skip", DEFAULT_CONFIG) is None
    assert import_type("import os  # isort: skip", DEFAULT_CONFIG) is None
    assert import_type("import os  # isort: split", DEFAULT_CONFIG) is None


def test_import_type_straight():
    assert import_type("import os", DEFAULT_CONFIG) == "straight"
    assert import_type("cimport numpy", DEFAULT_CONFIG) == "straight"


def test_import_type_from():
    assert import_type("from os import path", DEFAULT_CONFIG) == "from"


def test_import_type_none():
    assert import_type("print('hello')", DEFAULT_CONFIG) is None
