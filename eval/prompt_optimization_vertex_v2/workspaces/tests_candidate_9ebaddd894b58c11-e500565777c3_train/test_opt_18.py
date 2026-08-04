# file: src\sample_repo\isort\isort\main.py:962-972
# asked: {"lines": [962, 964, 965, 966, 967, 968, 969, 970, 971, 972], "branches": [[964, 965], [964, 966], [966, 967], [966, 968], [968, 969], [968, 970], [970, 971], [970, 972]]}
# gained: {"lines": [962, 964, 965, 966, 967, 968, 969, 970, 971, 972], "branches": [[964, 965], [964, 966], [966, 967], [966, 968], [968, 969], [968, 970], [970, 971], [970, 972]]}

from pathlib import Path
import pytest

from isort.main import _preconvert
from isort.wrap_modes import WrapModes


def test_preconvert_set_and_frozenset():
    assert sorted(_preconvert({1, 2})) == [1, 2]
    assert sorted(_preconvert(frozenset([3, 4]))) == [3, 4]


def test_preconvert_wrap_modes():
    # WrapModes is an Enum; let's pick any member, e.g., GRID
    mode = WrapModes.GRID
    assert _preconvert(mode) == str(mode.name)


def test_preconvert_path():
    p = Path("/some/path")
    assert _preconvert(p) == str(p)


def test_preconvert_callable():
    def sample_function():
        pass

    assert _preconvert(sample_function) == "sample_function"


def test_preconvert_type_error():
    with pytest.raises(TypeError, match="Unserializable object"):
        _preconvert(object())
