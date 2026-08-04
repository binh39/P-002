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
    # WrapModes is an Enum-like or IntEnum class depending on version
    # Let's pick a valid member from WrapModes if possible, or test all/any
    mode = list(WrapModes)[0]
    assert _preconvert(mode) == mode.name


def test_preconvert_path():
    p = Path("some/path")
    assert _preconvert(p) == str(p)


def test_preconvert_callable_with_name():
    def sample_func():
        pass

    assert _preconvert(sample_func) == "sample_func"


def test_preconvert_type_error():
    with pytest.raises(TypeError, match="Unserializable object"):
        _preconvert(object())
