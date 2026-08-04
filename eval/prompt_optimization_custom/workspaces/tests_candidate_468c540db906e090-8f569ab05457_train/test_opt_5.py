# file: src\sample_repo\isort\isort\settings.py:242-274
# asked: {"lines": [242, 243, 244, 245, 247, 248, 249, 251, 254, 255, 257, 258, 259, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273], "branches": [[244, 245], [244, 247], [247, 248], [247, 254], [254, 255], [254, 257], [257, 258], [257, 262], [262, 263], [262, 265], [265, 266], [265, 270], [270, 0], [270, 271]]}
# gained: {"lines": [242, 243, 244, 245, 247, 248, 249, 251, 254, 255, 257, 258, 259, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273], "branches": [[244, 245], [244, 247], [247, 248], [247, 254], [254, 255], [257, 258], [262, 263], [262, 265], [265, 266], [265, 270], [270, 0], [270, 271]]}

import pytest
import sys
from isort.settings import _Config
from isort.wrap_modes import WrapModes

VALID_PY_TARGETS = {"36", "37", "38", "39", "310", "311", "312", "313", "all"}

def test_post_init_auto_py_version():
    config = _Config(py_version="auto")
    assert config.py_version.startswith("py")  # Check if py_version is set correctly

def test_post_init_invalid_py_version():
    with pytest.raises(ValueError, match="The python version invalid is not supported"):
        _Config(py_version="invalid")

def test_post_init_valid_py_version():
    config = _Config(py_version="36")
    assert config.py_version == "py36"  # Check if py_version is set correctly

def test_post_init_known_standard_library():
    config = _Config(py_version="36")
    assert isinstance(config.known_standard_library, frozenset)  # Check if known_standard_library is a frozenset

def test_post_init_vertical_grid_grouped_mode():
    config = _Config(multi_line_output=WrapModes.VERTICAL_GRID_GROUPED_NO_COMMA)
    assert config.multi_line_output == WrapModes.VERTICAL_GRID_GROUPED  # Check if multi_line_output is updated

def test_post_init_force_alphabetical_sort():
    config = _Config(force_alphabetical_sort=True)
    assert config.force_alphabetical_sort_within_sections is True
    assert config.no_sections is True
    assert config.lines_between_types == 1
    assert config.from_first is True

def test_post_init_wrap_length_greater_than_line_length():
    with pytest.raises(ValueError, match="wrap_length must be set lower than or equal to line_length"):
        _Config(wrap_length=100, line_length=79)
