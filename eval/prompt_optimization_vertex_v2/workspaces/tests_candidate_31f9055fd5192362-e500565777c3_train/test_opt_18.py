# file: src\sample_repo\isort\isort\parse.py:53-63
# asked: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}
# gained: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}

import pytest
from isort.parse import import_type
from isort.settings import Config


def test_import_type_honor_noqa():
    # config.honor_noqa = True, ending with noqa
    config = Config(honor_noqa=True)
    assert import_type("import os  # NOQA", config) is None
    assert import_type("import os  # noqa", config) is None


def test_import_type_noqa_not_honored():
    # config.honor_noqa = False (default), ending with noqa should not return None immediately
    config = Config(honor_noqa=False)
    assert import_type("import os  # noqa", config) == "straight"


def test_import_type_skip_comments():
    config = Config(honor_noqa=False)
    assert import_type("import os  # isort:skip", config) is None
    assert import_type("import os  # isort: skip", config) is None
    assert import_type("import os  # isort: split", config) is None


def test_import_type_straight_imports():
    config = Config(honor_noqa=False)
    assert import_type("import os", config) == "straight"
    assert import_type("cimport numpy", config) == "straight"


def test_import_type_from_imports():
    config = Config(honor_noqa=False)
    assert import_type("from os import path", config) == "from"


def test_import_type_none():
    config = Config(honor_noqa=False)
    assert import_type("x = 1", config) is None
    assert import_type("", config) is None
