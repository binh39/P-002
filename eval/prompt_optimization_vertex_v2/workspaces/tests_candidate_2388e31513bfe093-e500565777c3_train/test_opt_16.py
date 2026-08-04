# file: src\sample_repo\isort\isort\parse.py:53-63
# asked: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}
# gained: {"lines": [53, 55, 56, 57, 58, 59, 60, 61, 62, 63], "branches": [[55, 56], [55, 57], [57, 58], [57, 59], [59, 60], [59, 61], [61, 62], [61, 63]]}

import pytest
from isort.parse import import_type
from isort.settings import Config


def test_import_type_honor_noqa_true_and_ends_with_noqa():
    # config.honor_noqa is True by default, line ends with noqa (case-insensitive, with trailing spaces)
    config = Config(honor_noqa=True)
    assert import_type("import os  # NOQA", config) is None
    assert import_type("from math import sin  # noqa", config) is None


def test_import_type_honor_noqa_false_and_ends_with_noqa():
    # config.honor_noqa is False, line ends with noqa should be ignored by the noqa check
    config = Config(honor_noqa=False)
    assert import_type("import os  # NOQA", config) == "straight"
    assert import_type("from math import sin  # noqa", config) == "from"


def test_import_type_honor_noqa_true_does_not_end_with_noqa():
    # config.honor_noqa is True, but line does not end with noqa
    config = Config(honor_noqa=True)
    assert import_type("import os # noqa comment in middle", config) == "straight"


@pytest.mark.parametrize(
    "skip_phrase",
    [
        "isort:skip",
        "isort: skip",
        "isort: split",
    ],
)
def test_import_type_skip_phrases(skip_phrase):
    # Tests matching isort:skip, isort: skip, and isort: split anywhere in line
    line_with_skip = f"import os # {skip_phrase}"
    assert import_type(line_with_skip) is None


def test_import_type_straight_imports():
    # Tests lines starting with 'import ' or 'cimport '
    assert import_type("import os") == "straight"
    assert import_type("cimport numpy") == "straight"


def test_import_type_from_import():
    # Tests lines starting with 'from '
    assert import_type("from os import path") == "from"


def test_import_type_none_fallback():
    # Lines that are not imports or match any skip/noqa conditions
    assert import_type("x = 1") is None
    assert import_type("") is None
    assert import_type("print('hello')") is None
