# file: src\sample_repo\isort\isort\parse.py:53-63
# asked: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}
# gained: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}

from isort.parse import import_type
from isort.settings import Config


def test_import_type_honor_noqa() -> None:
    config_honor = Config(honor_noqa=True)
    assert import_type("import os # NOQA", config=config_honor) is None
    assert import_type("import os # noqa", config=config_honor) is None

    config_no_honor = Config(honor_noqa=False)
    assert import_type("import os # noqa", config=config_no_honor) == "straight"


def test_import_type_skips() -> None:
    assert import_type("import os # isort:skip") is None
    assert import_type("import os # isort: skip") is None
    assert import_type("import os # isort: split") is None


def test_import_type_straight() -> None:
    assert import_type("import os") == "straight"
    assert import_type("cimport numpy") == "straight"


def test_import_type_from() -> None:
    assert import_type("from os import path") == "from"


def test_import_type_none() -> None:
    assert import_type("x = 1") is None
    assert import_type("importer = 5") is None
