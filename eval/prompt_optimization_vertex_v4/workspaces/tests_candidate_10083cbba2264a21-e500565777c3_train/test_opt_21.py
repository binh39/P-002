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
    # WrapModes is an Enum or similar
    mode = list(WrapModes)[0]
    assert _preconvert(mode) == str(mode.name)


def test_preconvert_path():
    path_obj = Path("/some/path")
    assert _preconvert(path_obj) == str(path_obj)


def test_preconvert_callable():
    def dummy_func():
        pass

    assert _preconvert(dummy_func) == "dummy_func"


def test_preconvert_type_error():
    class Unserializable:
        def __call__(self):
            # Callable without __name__ or just not matching the callable+__name__ condition properly,
            # or an entirely non-callable object like an object instance.
            pass

    # An instance of a class that is callable might not have __name__, or an object that is not callable.
    # Let's test an object that is not callable and not in any supported type.
    with pytest.raises(TypeError, match="Unserializable object"):
        _preconvert(object())
