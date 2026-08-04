# file: src\sample_repo\isort\isort\main.py:962-972
# asked: {"lines": [962, 964, 965, 966, 967, 968, 969, 970, 971, 972], "branches": [[964, 965], [964, 966], [966, 967], [966, 968], [968, 969], [968, 970], [970, 971], [970, 972]]}
# gained: {"lines": [962, 964, 965, 966, 967, 968, 969, 970, 971, 972], "branches": [[964, 965], [964, 966], [966, 967], [966, 968], [968, 969], [968, 970], [970, 971], [970, 972]]}

from pathlib import Path
import pytest

from isort.main import _preconvert
from isort.wrap_modes import WrapModes


def test_preconvert_set():
    s = {1, 2, 3}
    result = _preconvert(s)
    assert sorted(result) == [1, 2, 3]
    assert isinstance(result, list)


def test_preconvert_frozenset():
    fs = frozenset([4, 5])
    result = _preconvert(fs)
    assert sorted(result) == [4, 5]
    assert isinstance(result, list)


def test_preconvert_wrap_modes():
    # WrapModes is an Enum (or IntEnum), let's pick a valid member if available,
    # or test with any available member.
    mode = list(WrapModes)[0]
    result = _preconvert(mode)
    assert result == mode.name
    assert isinstance(result, str)


def test_preconvert_path():
    p = Path("/some/path")
    result = _preconvert(p)
    assert result == str(p)
    assert isinstance(result, str)


def test_preconvert_callable():
    def sample_func():
        pass

    result = _preconvert(sample_func)
    assert result == "sample_func"
    assert isinstance(result, str)


def test_preconvert_type_error():
    unserializable = object()
    with pytest.raises(TypeError) as exc_info:
        _preconvert(unserializable)
    assert "Unserializable object" in str(exc_info.value)
