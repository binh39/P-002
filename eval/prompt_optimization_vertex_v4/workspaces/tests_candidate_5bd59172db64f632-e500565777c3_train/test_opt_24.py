# file: src\sample_repo\isort\isort\parse.py:53-63
# asked: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}
# gained: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}

from isort.parse import import_type
from isort.settings import Config


def test_import_type_honor_noqa():
    config_noqa = Config(honor_noqa=True)
    # Ends with noqa (case-insensitive or with spaces before rstrip)
    assert import_type("import os  # NOQA", config=config_noqa) is None
    assert import_type("from math import sin # noqa", config=config_noqa) is None

    # honor_noqa is False by default or explicitly
    config_no_noqa = Config(honor_noqa=False)
    assert import_type("import os  # NOQA", config=config_no_noqa) == "straight"


def test_import_type_isort_skip_split():
    assert import_type("import os  # isort:skip", config=Config()) is None
    assert import_type("import os  # isort: skip", config=Config()) is None
    assert import_type("import os  # isort: split", config=Config()) is None


def test_import_type_straight_and_cimport():
    assert import_type("import os", config=Config()) == "straight"
    assert import_type("cimport numpy", config=Config()) == "straight"


def test_import_type_from():
    assert import_type("from os import path", config=Config()) == "from"


def test_import_type_none():
    assert import_type("x = 1", config=Config()) is None
