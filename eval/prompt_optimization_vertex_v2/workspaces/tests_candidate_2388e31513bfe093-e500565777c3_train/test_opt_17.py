# file: src\sample_repo\isort\isort\main.py:962-972
# asked: {"lines": [962, 964, 965, 966, 967, 968, 969, 970, 971, 972], "branches": [[964, 965], [964, 966], [966, 967], [966, 968], [968, 969], [968, 970], [970, 971], [970, 972]]}
# gained: {"lines": [962, 964, 965, 966, 967, 968, 969, 970, 971, 972], "branches": [[964, 965], [964, 966], [966, 967], [966, 968], [968, 969], [968, 970], [970, 971], [970, 972]]}

from pathlib import Path
import pytest

from isort.main import _preconvert
from isort.wrap_modes import WrapModes


def test_preconvert_set():
    s = {1, 2, 3}
    res = _preconvert(s)
    assert isinstance(res, list)
    assert set(res) == s


def test_preconvert_frozenset():
    fs = frozenset([4, 5, 6])
    res = _preconvert(fs)
    assert isinstance(res, list)
    assert set(res) == set(fs)


def test_preconvert_wrap_modes():
    # WrapModes is an Enum; let's pick a valid member
    mode = list(WrapModes)[0]
    res = _preconvert(mode)
    assert res == mode.name


def test_preconvert_path():
    p = Path("/some/path")
    res = _preconvert(p)
    assert res == str(p)


def test_preconvert_callable_with_name():
    def sample_func():
        pass

    res = _preconvert(sample_func)
    assert res == "sample_func"


def test_preconvert_callable_without_name():
    # A callable object or lambda that lacks __name__ or is not caught by hasattr(..., "__name__")
    # Actually, functions always have __name__, but some callables might not.
    # What about a custom class instance that is callable but doesn't have __name__?
    class CallableWithoutName:
        def __call__(self):
            pass

    obj = CallableWithoutName()
    # It is callable, but does not have __name__, so it should fall through to TypeError.
    with pytest.raises(TypeError, match="Unserializable object"):
        _preconvert(obj)


def test_preconvert_unserializable():
    with pytest.raises(TypeError, match="Unserializable object"):
        _preconvert(object())
