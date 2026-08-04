# file: src\sample_repo\isort\isort\parse.py:53-63
# asked: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}
# gained: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}

from isort.parse import import_type
from isort.settings import Config


def test_import_type_honor_noqa() -> None:
    config = Config(honor_noqa=True)
    # Ends with noqa (case insensitive, stripped)
    assert import_type("import os  # NOQA", config) is None
    assert import_type("import sys  # noqa", config) is None

    # honor_noqa = False should not skip noqa
    config_no_honor = Config(honor_noqa=False)
    assert import_type("import os  # noqa", config_no_honor) == "straight"


def test_import_type_isort_skip_split() -> None:
    assert import_type("import os  # isort:skip") is None
    assert import_type("import os  # isort: skip") is None
    assert import_type("import os  # isort: split") is None


def test_import_type_straight() -> None:
    assert import_type("import os") == "straight"
    assert import_type("cimport numpy") == "straight"


def test_import_type_from() -> None:
    assert import_type("from os import path") == "from"


def test_import_type_none() -> None:
    assert import_type("x = 1") is None
    assert import_type("") is None
