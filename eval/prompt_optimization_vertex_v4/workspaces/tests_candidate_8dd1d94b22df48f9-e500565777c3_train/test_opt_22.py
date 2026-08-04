# file: src\sample_repo\isort\isort\parse.py:53-63
# asked: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}
# gained: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}

from isort.parse import import_type
from isort.settings import Config


def test_import_type_honor_noqa_true():
    config = Config(honor_noqa=True)
    assert import_type("import os  # NOQA", config) is None
    assert import_type("import os  # noqa", config) is None


def test_import_type_honor_noqa_false_with_noqa():
    config = Config(honor_noqa=False)
    assert import_type("import os  # noqa", config) == "straight"


def test_import_type_skip_directives():
    assert import_type("import os  # isort:skip", DEFAULT_CONFIG if 'DEFAULT_CONFIG' in globals() else Config()) is None
    assert import_type("import os  # isort: skip", Config()) is None
    assert import_type("import os  # isort: split", Config()) is None


def test_import_type_straight_imports():
    assert import_type("import os", Config()) == "straight"
    assert import_type("cimport numpy", Config()) == "straight"


def test_import_type_from_import():
    assert import_type("from os import path", Config()) == "from"


def test_import_type_none():
    assert import_type("print('hello')", Config()) is None
    assert import_type("", Config()) is None
