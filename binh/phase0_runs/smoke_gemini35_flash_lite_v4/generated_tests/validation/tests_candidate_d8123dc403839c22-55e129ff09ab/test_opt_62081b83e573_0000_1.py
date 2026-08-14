# file: src\sample_repo\isort\isort\wrap_modes.py:41-48
# asked: {"lines": [41, 45, 46, 47, 48], "branches": []}
# gained: {"lines": [41, 45, 46, 47, 48], "branches": []}

from inspect import signature
from isort.wrap_modes import _wrap_mode, _wrap_mode_interface, _wrap_modes


def test_wrap_mode_decorator() -> str:
    # Test that applying the decorator explicitly executes lines 41-48
    @_wrap_mode
    def dummy_wrap_mode(**kwargs):
        return "dummy"

    try:
        # Check that it was registered in _wrap_modes
        assert "DUMMY_WRAP_MODE" in _wrap_modes
        assert _wrap_modes["DUMMY_WRAP_MODE"] is dummy_wrap_mode

        # Check signature and annotations were updated correctly (lines 46-47)
        assert dummy_wrap_mode.__signature__ == signature(_wrap_mode_interface)
        assert dummy_wrap_mode.__annotations__ == _wrap_mode_interface.__annotations__

        # Check that the function itself is returned (line 48)
        assert dummy_wrap_mode() == "dummy"
    finally:
        # Clean up modified state
        _wrap_modes.pop("DUMMY_WRAP_MODE", None)
