# file: src\sample_repo\isort\isort\parse.py:53-63
# asked: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}
# gained: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}

import pytest
from isort.parse import import_type
from isort.settings import Config


def test_import_type_honor_noqa():
    config_honor = Config(honor_noqa=True)
    config_no_honor = Config(honor_noqa=False)

    # Line ending with noqa with honor_noqa=True -> None
    assert import_type("import os  # NOQA", config=config_honor) is None
    # Line ending with noqa with honor_noqa=False -> should check other conditions (e.g. straight)
    assert import_type("import os  # NOQA", config=config_no_honor) == "straight"


def test_import_type_skip_directives():
    assert import_type("import os  # isort:skip") is None
    assert import_type("import os  # isort: skip") is None
    assert import_type("import os  # isort: split") is None


def test_import_type_straight_imports():
    assert import_type("import os") == "straight"
    assert import_type("cimport module") == "straight"


def test_import_type_from_imports():
    assert import_type("from os import path") == "from"


def test_import_type_none():
    assert import_type("x = 1") is None
    assert import_type("") is None
