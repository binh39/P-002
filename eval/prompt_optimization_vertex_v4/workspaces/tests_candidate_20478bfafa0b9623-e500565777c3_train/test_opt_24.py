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
    # Since sets are unordered, we can assert it's a list containing the elements
    assert isinstance(result, list)
    assert set(result) == s


def test_preconvert_frozenset():
    fs = frozenset([4, 5])
    result = _preconvert(fs)
    assert isinstance(result, list)
    assert set(result) == set(fs)


def test_preconvert_wrap_modes():
    # WrapModes is an Enum or similar class
    mode = WrapModes.GRID
    result = _preconvert(mode)
    assert result == "GRID"


def test_preconvert_path():
    p = Path("/some/path/to/file")
    result = _preconvert(p)
    assert result == str(p)


def test_preconvert_callable_with_name():
    def sample_func():
        pass

    result = _preconvert(sample_func)
    assert result == "sample_func"


def test_preconvert_type_error():
    class UnserializableClass:
        pass

    obj = UnserializableClass()
    with pytest.raises(TypeError, match="Unserializable object"):
        _preconvert(obj)
