# file: src\sample_repo\isort\isort\settings.py:242-274
# asked: {"lines": [242, 243, 244, 245, 247, 248, 249, 251, 254, 255, 257, 258, 259, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273], "branches": [[244, 245], [244, 247], [247, 248], [247, 254], [254, 255], [254, 257], [257, 258], [257, 262], [262, 263], [262, 265], [265, 266], [265, 270], [270, 0], [270, 271]]}
# gained: {"lines": [242, 243, 244, 247, 248, 249, 251, 254, 255, 257, 258, 259, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273], "branches": [[244, 247], [247, 248], [247, 254], [254, 255], [254, 257], [257, 258], [257, 262], [262, 263], [262, 265], [265, 266], [265, 270], [270, 0], [270, 271]]}

import pytest
from isort.settings import _Config
from isort.wrap_modes import WrapModes


def test_config_post_init_lines_242_273():
    # 1. Invalid python version -> raises ValueError (lines 247-251)
    with pytest.raises(ValueError, match="The python version invalid is not supported"):
        _Config(py_version="invalid")

    # 2. py_version == "all" -> bypasses version formatting (line 254)
    config_all = _Config(py_version="all")
    assert config_all.py_version == "all"

    # 3. known_standard_library provided -> doesn't overwrite (line 257)
    custom_stdlib = frozenset(["os", "sys"])
    config_custom_stdlib = _Config(py_version="3", known_standard_library=custom_stdlib)
    assert config_custom_stdlib.known_standard_library == custom_stdlib

    # 4. multi_line_output == WrapModes.VERTICAL_GRID_GROUPED_NO_COMMA -> maps to VERTICAL_GRID_GROUPED (lines 262-264)
    config_vgg_nc = _Config(py_version="3", multi_line_output=WrapModes.VERTICAL_GRID_GROUPED_NO_COMMA)
    assert config_vgg_nc.multi_line_output == WrapModes.VERTICAL_GRID_GROUPED

    # 5. force_alphabetical_sort -> sets several attributes (lines 265-269)
    config_fas = _Config(py_version="3", force_alphabetical_sort=True)
    assert config_fas.force_alphabetical_sort_within_sections is True
    assert config_fas.no_sections is True
    assert config_fas.lines_between_types == 1
    assert config_fas.from_first is True

    # 6. wrap_length > line_length -> raises ValueError (lines 270-273)
    with pytest.raises(ValueError, match="wrap_length must be set lower than or equal to line_length"):
        _Config(py_version="3", line_length=80, wrap_length=81)
