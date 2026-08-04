# file: src\sample_repo\isort\isort\settings.py:242-274
# asked: {"lines": [242, 243, 244, 245, 247, 248, 249, 251, 254, 255, 257, 258, 259, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273], "branches": [[244, 245], [244, 247], [247, 248], [247, 254], [254, 255], [254, 257], [257, 258], [257, 262], [262, 263], [262, 265], [265, 266], [265, 270], [270, 0], [270, 271]]}
# gained: {"lines": [242, 243, 244, 247, 248, 249, 251, 254, 255, 257, 258, 259, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273], "branches": [[244, 247], [247, 248], [247, 254], [254, 255], [257, 258], [262, 263], [262, 265], [265, 266], [265, 270], [270, 0], [270, 271]]}

import pytest
from isort.settings import Config, VALID_PY_TARGETS
from isort.wrap_modes import WrapModes


def test_config_invalid_py_version():
    with pytest.raises(ValueError, match="is not supported"):
        Config(py_version="invalid_version_xyz")


def test_config_vertical_grid_grouped_no_comma():
    config = Config(multi_line_output=WrapModes.VERTICAL_GRID_GROUPED_NO_COMMA)
    assert config.multi_line_output == WrapModes.VERTICAL_GRID_GROUPED


def test_config_force_alphabetical_sort():
    config = Config(force_alphabetical_sort=True)
    assert config.force_alphabetical_sort_within_sections is True
    assert config.no_sections is True
    assert config.lines_between_types == 1
    assert config.from_first is True


def test_config_wrap_length_greater_than_line_length():
    with pytest.raises(ValueError, match="wrap_length must be set lower than or equal to line_length"):
        Config(line_length=80, wrap_length=100)
