# file: src\sample_repo\isort\isort\parse.py:53-63
# asked: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}
# gained: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}

from isort.parse import import_type
from isort.settings import Config


def test_import_type_honor_noqa_true():
    config = Config(honor_noqa=True)
    # Ends with noqa (case-insensitive and trailing whitespace)
    assert import_type("import os # NOQA", config) is None
    assert import_type("import os  noqa  ", config) is None


def test_import_type_honor_noqa_false():
    config = Config(honor_noqa=False)
    # Even if line ends with noqa, it should not return None due to noqa if honor_noqa is False
    # But wait, isort:skip checks happen right after. Let's make sure it doesn't match skip.
    assert import_type("import os # NOQA", config) == "straight"


def test_import_type_skip_comments():
    assert import_type("import os # isort:skip", DEFAULT_CONFIG := Config()) is None
    assert import_type("import os # isort: skip", DEFAULT_CONFIG) is None
    assert import_type("import os # isort: split", DEFAULT_CONFIG) is None


def test_import_type_straight_imports():
    assert import_type("import os") == "straight"
    assert import_type("cimport numpy") == "straight"


def test_import_type_from_imports():
    assert import_type("from os import path") == "from"


def test_import_type_none():
    assert import_type("print('hello')") is None
