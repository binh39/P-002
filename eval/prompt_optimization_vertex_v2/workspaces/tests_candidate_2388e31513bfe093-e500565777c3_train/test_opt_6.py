# file: src\sample_repo\isort\isort\settings.py:242-274
# asked: {"lines": [242, 243, 244, 245, 247, 248, 249, 251, 254, 255, 257, 258, 259, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273], "branches": [[244, 245], [244, 247], [247, 248], [247, 254], [254, 255], [254, 257], [257, 258], [257, 262], [262, 263], [262, 265], [265, 266], [265, 270], [270, 0], [270, 271]]}
# gained: {"lines": [242, 243, 244, 247, 248, 249, 251, 254, 255, 257, 258, 259, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273], "branches": [[244, 247], [247, 248], [247, 254], [254, 255], [254, 257], [257, 258], [257, 262], [262, 263], [262, 265], [265, 266], [265, 270], [270, 0], [270, 271]]}

import pytest
import sys
from isort.settings import _Config, VALID_PY_TARGETS
from isort.wrap_modes import WrapModes


def test_config_invalid_py_version():
    with pytest.raises(ValueError, match="The python version invalid_version is not supported"):
        _Config(py_version="invalid_version")


def test_config_py_version_all():
    config = _Config(py_version="all")
    assert config.py_version == "all"
    assert len(config.known_standard_library) > 0


def test_config_py_version_specific():
    config = _Config(py_version="38")
    assert config.py_version == "py38"
    assert len(config.known_standard_library) > 0


def test_config_known_standard_library_explicit():
    custom_stdlib = frozenset(["os", "sys"])
    config = _Config(py_version="38", known_standard_library=custom_stdlib)
    assert config.known_standard_library == custom_stdlib


def test_config_multi_line_output_vertical_grid_grouped_no_comma():
    config = _Config(multi_line_output=WrapModes.VERTICAL_GRID_GROUPED_NO_COMMA)
    assert config.multi_line_output == WrapModes.VERTICAL_GRID_GROUPED


def test_config_multi_line_output_other():
    config = _Config(multi_line_output=WrapModes.GRID)
    assert config.multi_line_output == WrapModes.GRID


def test_config_force_alphabetical_sort_true():
    config = _Config(force_alphabetical_sort=True)
    assert config.force_alphabetical_sort_within_sections is True
    assert config.no_sections is True
    assert config.lines_between_types == 1
    assert config.from_first is True


def test_config_force_alphabetical_sort_false():
    config = _Config(
        force_alphabetical_sort=False,
        force_alphabetical_sort_within_sections=False,
        no_sections=False,
        lines_between_types=0,
        from_first=False,
    )
    assert config.force_alphabetical_sort_within_sections is False
    assert config.no_sections is False
    assert config.lines_between_types == 0
    assert config.from_first is False


def test_config_wrap_length_valid():
    config = _Config(line_length=80, wrap_length=40)
    assert config.wrap_length == 40
    assert config.line_length == 80


def test_config_wrap_length_equal():
    config = _Config(line_length=80, wrap_length=80)
    assert config.wrap_length == 80
    assert config.line_length == 80


def test_config_wrap_length_invalid():
    with pytest.raises(ValueError, match="wrap_length must be set lower than or equal to line_length: 90 > 80."):
        _Config(line_length=80, wrap_length=90)
