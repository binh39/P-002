# file: src\sample_repo\isort\isort\settings.py:242-274
# asked: {"lines": [242, 243, 244, 245, 247, 248, 249, 251, 254, 255, 257, 258, 259, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273], "branches": [[244, 245], [244, 247], [247, 248], [247, 254], [254, 255], [254, 257], [257, 258], [257, 262], [262, 263], [262, 265], [265, 266], [265, 270], [270, 0], [270, 271]]}
# gained: {"lines": [242, 243, 244, 247, 248, 249, 251, 254, 255, 257, 258, 259, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273], "branches": [[244, 247], [247, 248], [247, 254], [254, 255], [254, 257], [257, 258], [257, 262], [262, 263], [262, 265], [265, 266], [265, 270], [270, 0], [270, 271]]}

import pytest
from isort.settings import _Config, VALID_PY_TARGETS
from isort.wrap_modes import WrapModes


def test_config_post_init_valid_targets_and_defaults():
    # Tests a valid py_version (not "all") from VALID_PY_TARGETS
    # Also tests known_standard_library populated when empty.
    # Also tests multi_line_output != VERTICAL_GRID_GROUPED_NO_COMMA, force_alphabetical_sort = False, wrap_length <= line_length
    non_all_targets = [t for t in VALID_PY_TARGETS if t != "all"]
    target = non_all_targets[0]
    cfg = _Config(py_version=target)
    assert cfg.py_version == f"py{target}"
    assert isinstance(cfg.known_standard_library, frozenset)
    assert len(cfg.known_standard_library) > 0


def test_config_post_init_py_version_all():
    # Tests py_version == "all" branch where object.__setattr__(self, "py_version", ...) is skipped.
    cfg = _Config(py_version="all")
    assert cfg.py_version == "all"


def test_config_post_init_invalid_py_version():
    # Tests py_version not in VALID_PY_TARGETS raises ValueError.
    with pytest.raises(ValueError, match="is not supported"):
        _Config(py_version="invalid_version_999")


def test_config_post_init_known_standard_library_provided():
    # Tests when known_standard_library is already provided (non-empty), so stdlibs population is skipped.
    custom_stdlib = frozenset(["custom_module"])
    cfg = _Config(known_standard_library=custom_stdlib)
    assert cfg.known_standard_library == custom_stdlib


def test_config_post_init_vertical_grid_grouped_no_comma():
    # Tests multi_line_output == WrapModes.VERTICAL_GRID_GROUPED_NO_COMMA gets converted to VERTICAL_GRID_GROUPED.
    cfg = _Config(multi_line_output=WrapModes.VERTICAL_GRID_GROUPED_NO_COMMA)
    assert cfg.multi_line_output == WrapModes.VERTICAL_GRID_GROUPED


def test_config_post_init_force_alphabetical_sort():
    # Tests force_alphabetical_sort = True updates multiple attributes.
    cfg = _Config(force_alphabetical_sort=True)
    assert cfg.force_alphabetical_sort_within_sections is True
    assert cfg.no_sections is True
    assert cfg.lines_between_types == 1
    assert cfg.from_first is True


def test_config_post_init_wrap_length_greater_than_line_length():
    # Tests wrap_length > line_length raises ValueError.
    with pytest.raises(ValueError, match="wrap_length must be set lower than or equal to line_length"):
        _Config(wrap_length=100, line_length=80)
