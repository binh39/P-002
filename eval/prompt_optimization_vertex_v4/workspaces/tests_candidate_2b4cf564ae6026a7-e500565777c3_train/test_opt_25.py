# file: src\sample_repo\isort\isort\main.py:962-972
# asked: {"lines": [962, 964, 965, 966, 967, 968, 969, 970, 971, 972], "branches": [[964, 965], [964, 966], [966, 967], [966, 968], [968, 969], [968, 970], [970, 971], [970, 972]]}
# gained: {"lines": [962, 964, 965, 966, 967, 968, 969, 970, 971, 972], "branches": [[964, 965], [964, 966], [966, 967], [966, 968], [968, 969], [968, 970], [970, 971], [970, 972]]}

import pytest
from pathlib import Path
from isort.main import _preconvert
from isort.wrap_modes import WrapModes


def test_preconvert_set():
    s = {1, 2, 3}
    res = _preconvert(s)
    assert sorted(res) == [1, 2, 3]


def test_preconvert_frozenset():
    fs = frozenset([4, 5])
    res = _preconvert(fs)
    assert sorted(res) == [4, 5]


def test_preconvert_wrap_modes():
    mode = WrapModes.VERTICAL
    assert _preconvert(mode) == mode.name


def test_preconvert_path():
    p = Path("some/path")
    assert _preconvert(p) == str(p)


def test_preconvert_callable():
    def dummy_func():
        pass

    assert _preconvert(dummy_func) == "dummy_func"


def test_preconvert_unserializable():
    class Unserializable:
        def __call__(self):
            pass

    # If it's an instance of a class with __call__, it's callable,
    # but instances typically do not have a "__name__" attribute unless set explicitly.
    # This should trigger line 970 (callable is True, but hasattr(item, "__name__") is False)
    # and then raise TypeError on line 972.
    obj = Unserializable()
    with pytest.raises(TypeError, match="Unserializable object"):
        _preconvert(obj)

    # Also test an object that is neither callable, nor set/frozenset, nor WrapModes, nor Path
    with pytest.raises(TypeError, match="Unserializable object"):
        _preconvert(12345)
