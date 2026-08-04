# file: src\sample_repo\isort\isort\settings.py:242-274
# asked: {"lines": [242, 243, 244, 245, 247, 248, 249, 251, 254, 255, 257, 258, 259, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273], "branches": [[244, 245], [244, 247], [247, 248], [247, 254], [254, 255], [254, 257], [257, 258], [257, 262], [262, 263], [262, 265], [265, 266], [265, 270], [270, 0], [270, 271]]}
# gained: {"lines": [242, 243, 244, 247, 248, 249, 251, 254, 255, 257, 258, 259, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273], "branches": [[244, 247], [247, 248], [247, 254], [254, 255], [254, 257], [257, 258], [257, 262], [262, 263], [262, 265], [265, 266], [265, 270], [270, 0], [270, 271]]}

import pytest
import sys
from dataclasses import dataclass
from isort.settings import _Config, VALID_PY_TARGETS
from isort.wrap_modes import WrapModes


def test_config_post_init_valid_targets_and_defaults():
    # Test valid python target (excluding "all" if it's the first element)
    non_all_targets = [t for t in VALID_PY_TARGETS if t != "all"]
    target = non_all_targets[0]
    config = _Config(py_version=target)
    assert config.py_version == f"py{target}"


def test_config_post_init_py_version_all():
    # Test py_version == "all" (should not prefix with "py")
    config = _Config(py_version="all")
    assert config.py_version == "all"


def test_config_post_init_invalid_py_version():
    # Test invalid py_version raises ValueError
    with pytest.raises(ValueError) as exc_info:
        _Config(py_version="invalid_version")
    assert "The python version invalid_version is not supported" in str(exc_info.value)


def test_config_post_init_known_standard_library_explicit():
    # Test when known_standard_library is explicitly provided
    custom_stdlib = frozenset(["os", "sys"])
    non_all_targets = [t for t in VALID_PY_TARGETS if t != "all"]
    config = _Config(py_version=non_all_targets[0], known_standard_library=custom_stdlib)
    assert config.known_standard_library == custom_stdlib


def test_config_post_init_vertical_grid_grouped_no_comma():
    # Test multi_line_output WrapModes.VERTICAL_GRID_GROUPED_NO_COMMA transformation
    non_all_targets = [t for t in VALID_PY_TARGETS if t != "all"]
    config = _Config(
        py_version=non_all_targets[0],
        multi_line_output=WrapModes.VERTICAL_GRID_GROUPED_NO_COMMA
    )
    assert config.multi_line_output == WrapModes.VERTICAL_GRID_GROUPED


def test_config_post_init_force_alphabetical_sort():
    # Test force_alphabetical_sort triggers multiple object attributes
    non_all_targets = [t for t in VALID_PY_TARGETS if t != "all"]
    config = _Config(
        py_version=non_all_targets[0],
        force_alphabetical_sort=True
    )
    assert config.force_alphabetical_sort_within_sections is True
    assert config.no_sections is True
    assert config.lines_between_types == 1
    assert config.from_first is True


def test_config_post_init_wrap_length_exceeds_line_length():
    # Test wrap_length > line_length raises ValueError
    non_all_targets = [t for t in VALID_PY_TARGETS if t != "all"]
    with pytest.raises(ValueError) as exc_info:
        _Config(
            py_version=non_all_targets[0],
            line_length=80,
            wrap_length=100
        )
    assert "wrap_length must be set lower than or equal to line_length" in str(exc_info.value)


def test_config_post_init_wrap_length_equal_line_length():
    # Test wrap_length == line_length is valid (does not raise ValueError)
    non_all_targets = [t for t in VALID_PY_TARGETS if t != "all"]
    config = _Config(
        py_version=non_all_targets[0],
        line_length=80,
        wrap_length=80
    )
    assert config.wrap_length == 80
    assert config.line_length == 80
