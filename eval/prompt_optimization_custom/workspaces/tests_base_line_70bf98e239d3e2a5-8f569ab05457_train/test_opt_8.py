# file: src\sample_repo\isort\isort\settings.py:242-274
# asked: {"lines": [242, 243, 244, 245, 247, 248, 249, 251, 254, 255, 257, 258, 259, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273], "branches": [[244, 245], [244, 247], [247, 248], [247, 254], [254, 255], [254, 257], [257, 258], [257, 262], [262, 263], [262, 265], [265, 266], [265, 270], [270, 0], [270, 271]]}
# gained: {"lines": [242, 243, 244, 245, 247, 248, 249, 251, 254, 255, 257, 258, 259, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273], "branches": [[244, 245], [244, 247], [247, 248], [247, 254], [254, 255], [257, 258], [262, 263], [262, 265], [265, 266], [265, 270], [270, 0], [270, 271]]}

import sys
import pytest
from isort import stdlibs
from isort.wrap_modes import WrapModes
from isort.settings import _Config

# Define VALID_PY_TARGETS for testing purposes
VALID_PY_TARGETS = {"3", "3.6", "3.7", "3.8", "3.9", "3.10", "3.11", "all", "2", "27"}

@pytest.fixture
def config():
    """Fixture to create a default _Config instance."""
    return _Config()

def test_post_init_auto_py_version(config):
    """Test __post_init__ with 'auto' py_version."""
    config_with_auto = _Config(py_version="auto")
    assert config_with_auto.py_version.startswith("py")

def test_post_init_invalid_py_version(config):
    """Test __post_init__ raises ValueError for invalid py_version."""
    with pytest.raises(ValueError, match="The python version py3 is not supported"):
        _Config(py_version="py3")



def test_post_init_vertical_grid_grouped(config):
    """Test __post_init__ changes multi_line_output for specific mode."""
    config_with_vertical_grid = _Config(multi_line_output=WrapModes.VERTICAL_GRID_GROUPED_NO_COMMA)
    assert config_with_vertical_grid.multi_line_output == WrapModes.VERTICAL_GRID_GROUPED

def test_post_init_force_alphabetical_sort(config):
    """Test __post_init__ sets flags for force_alphabetical_sort."""
    config_with_sort = _Config(force_alphabetical_sort=True)
    assert config_with_sort.force_alphabetical_sort_within_sections
    assert config_with_sort.no_sections
    assert config_with_sort.lines_between_types == 1
    assert config_with_sort.from_first

def test_post_init_wrap_length_greater_than_line_length(config):
    """Test __post_init__ raises ValueError if wrap_length > line_length."""
    with pytest.raises(ValueError, match="wrap_length must be set lower than or equal to line_length"):
        _Config(wrap_length=100, line_length=80)
