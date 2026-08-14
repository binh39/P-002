# file: src\sample_repo\isort\isort\wrap_modes.py:41-48
# asked: {"lines": [41, 45, 46, 47, 48], "branches": []}
# gained: {"lines": [41, 45, 46, 47, 48], "branches": []}

from inspect import signature
import pytest
from isort.wrap_modes import _wrap_mode, _wrap_mode_interface, _wrap_modes


def test_wrap_mode_decorator():
    # Test registering a custom wrap mode function via the _wrap_mode decorator
    @_wrap_mode
    def custom_test_mode(**kwargs):
        return "custom"

    try:
        # Check that it was registered in _wrap_modes with uppercase name
        assert "CUSTOM_TEST_MODE" in _wrap_modes
        assert _wrap_modes["CUSTOM_TEST_MODE"] is custom_test_mode

        # Check signature and annotations were updated to _wrap_mode_interface
        assert custom_test_mode.__signature__ == signature(_wrap_mode_interface)
        assert custom_test_mode.__annotations__ == _wrap_mode_interface.__annotations__

        # Check return value
        assert custom_test_mode() == "custom"
    finally:
        # Clean up modified state
        _wrap_modes.pop("CUSTOM_TEST_MODE", None)
