# file: src\sample_repo\isort\isort\main.py:962-972
# asked: {"lines": [962, 964, 965, 966, 967, 968, 969, 970, 971, 972], "branches": [[964, 965], [964, 966], [966, 967], [966, 968], [968, 969], [968, 970], [970, 971], [970, 972]]}
# gained: {"lines": [962, 964, 965, 966, 967, 968, 969, 970, 971, 972], "branches": [[964, 965], [964, 966], [966, 967], [966, 968], [968, 969], [968, 970], [970, 971], [970, 972]]}

from pathlib import Path
import pytest

from isort.main import _preconvert
from isort.wrap_modes import WrapModes


def test_preconvert_set_and_frozenset():
    assert sorted(_preconvert({1, 2, 3})) == [1, 2, 3]
    assert sorted(_preconvert(frozenset([4, 5, 6]))) == [4, 5, 6]


def test_preconvert_wrap_modes():
    # WrapModes is an Enum, pick a valid member if available, or test with any member.
    # Let's inspect or use WrapModes values. Usually WrapModes has members like GRID, VERTICAL, etc.
    first_wrap_mode = list(WrapModes)[0]
    assert _preconvert(first_wrap_mode) == first_wrap_mode.name


def test_preconvert_path():
    path = Path("/some/path")
    assert _preconvert(path) == str(path)


def test_preconvert_callable():
    def sample_func():
        pass

    assert _preconvert(sample_func) == "sample_func"


def test_preconvert_type_error():
    class UncallableNoName:
        def __call__(self):
            pass
        # Remove __name__ if possible or use an object that is callable without __name__ 
        # or simply not callable.
    
    # Wait, functions usually have __name__. What about a custom callable object without __name__?
    class CustomCallable:
        def __call__(self):
            pass
        # Delete or ensure no __name__
        @property
        def __name__(self):
            raise AttributeError("no name")

    obj = CustomCallable()
    with pytest.raises(TypeError, match="Unserializable object"):
        _preconvert(obj)

    # Also test a completely non-callable, non-matched object
    with pytest.raises(TypeError, match="Unserializable object"):
        _preconvert(object())
