# file: src\sample_repo\isort\isort\parse.py:53-63
# asked: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}
# gained: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}

import pytest
from isort.parse import import_type
from isort.settings import Config


def test_import_type_honor_noqa():
    # config.honor_noqa = True by default or explicit, but let's check config with honor_noqa=True
    config = Config(honor_noqa=True)
    assert import_type("import os  # NOQA", config) is None
    assert import_type("import os  # noqa", config) is None

    # config.honor_noqa = False should not return None for noqa unless other rules match
    config_no_noqa = Config(honor_noqa=False)
    assert import_type("import os  # noqa", config_no_noqa) == "straight"


def test_import_type_skip_comments():
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
    assert import_type("  import os") is None  # doesn't start with "import " directly
