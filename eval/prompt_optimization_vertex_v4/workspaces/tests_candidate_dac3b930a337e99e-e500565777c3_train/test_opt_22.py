# file: src\sample_repo\isort\isort\main.py:962-972
# asked: {"lines": [962, 964, 965, 966, 967, 968, 969, 970, 971, 972], "branches": [[964, 965], [964, 966], [966, 967], [966, 968], [968, 969], [968, 970], [970, 971], [970, 972]]}
# gained: {"lines": [962, 964, 965, 966, 967, 968, 969, 970, 971, 972], "branches": [[964, 965], [964, 966], [966, 967], [966, 968], [968, 969], [968, 970], [970, 971], [970, 972]]}

from pathlib import Path
import pytest
from isort.main import _preconvert
from isort.wrap_modes import WrapModes


def test_preconvert_set():
    assert sorted(_preconvert({1, 2})) == [1, 2]


def test_preconvert_frozenset():
    assert sorted(_preconvert(frozenset([1, 2]))) == [1, 2]


def test_preconvert_wrap_modes():
    # WrapModes is an Enum-like class or IntEnum
    mode = list(WrapModes)[0]
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
            # Callable, but no __name__ attribute on the instance or class directly matching the condition?
            # Wait, functions have __name__. What about a callable object without __name__?
            pass

    # Let's check callable without __name__ or not callable at all
    with pytest.raises(TypeError, match="Unserializable object"):
        _preconvert(object())
