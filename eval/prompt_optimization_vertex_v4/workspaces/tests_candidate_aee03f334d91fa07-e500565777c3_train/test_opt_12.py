# file: src\sample_repo\isort\isort\settings.py:242-274
# asked: {"lines": [242, 243, 244, 245, 247, 248, 249, 251, 254, 255, 257, 258, 259, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273], "branches": [[244, 245], [244, 247], [247, 248], [247, 254], [254, 255], [254, 257], [257, 258], [257, 262], [262, 263], [262, 265], [265, 266], [265, 270], [270, 0], [270, 271]]}
# gained: {"lines": [242, 243, 244, 247, 254, 255, 257, 258, 259, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273], "branches": [[244, 247], [247, 254], [254, 255], [257, 258], [262, 263], [262, 265], [265, 266], [265, 270], [270, 0], [270, 271]]}

import pytest
from isort.settings import _Config, Config
from isort.wrap_modes import WrapModes


def test_config_vertical_grid_grouped_no_comma():
    # Tests line 262-264: multi_line_output == WrapModes.VERTICAL_GRID_GROUPED_NO_COMMA
    cfg = Config(multi_line_output=WrapModes.VERTICAL_GRID_GROUPED_NO_COMMA)
    assert cfg.multi_line_output == WrapModes.VERTICAL_GRID_GROUPED


def test_config_force_alphabetical_sort():
    # Tests lines 265-269: force_alphabetical_sort triggers setting changes
    cfg = Config(force_alphabetical_sort=True)
    assert cfg.force_alphabetical_sort_within_sections is True
    assert cfg.no_sections is True
    assert cfg.lines_between_types == 1
    assert cfg.from_first is True


def test_config_wrap_length_greater_than_line_length():
    # Tests lines 270-273: wrap_length > line_length raises ValueError
    with pytest.raises(ValueError, match="wrap_length must be set lower than or equal to line_length"):
        Config(line_length=50, wrap_length=60)
