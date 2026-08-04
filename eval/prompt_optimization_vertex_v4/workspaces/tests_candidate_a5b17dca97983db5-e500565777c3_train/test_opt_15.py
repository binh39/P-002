# file: src\sample_repo\isort\isort\settings.py:242-274
# asked: {"lines": [242, 243, 244, 245, 247, 248, 249, 251, 254, 255, 257, 258, 259, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273], "branches": [[244, 245], [244, 247], [247, 248], [247, 254], [254, 255], [254, 257], [257, 258], [257, 262], [262, 263], [262, 265], [265, 266], [265, 270], [270, 0], [270, 271]]}
# gained: {"lines": [242, 243, 244, 247, 248, 249, 251, 254, 255, 257, 258, 259, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273], "branches": [[244, 247], [247, 248], [247, 254], [254, 255], [254, 257], [257, 258], [262, 263], [262, 265], [265, 266], [265, 270], [270, 0], [270, 271]]}

import pytest
import sys
from isort.settings import _Config, VALID_PY_TARGETS
from isort.wrap_modes import WrapModes

def test_config_post_init_branches():
    # 1. Test VALID_PY_TARGETS exception/ValueError branch
    with pytest.raises(ValueError, match="is not supported"):
        _Config(py_version="invalid_version_999")

    # 2. Test py_version == "all" branch (does not prepend "py")
    config_all = _Config(py_version="all")
    assert config_all.py_version == "all"

    # 3. Test known_standard_library when not specified (uses stdlibs based on py_version)
    # Using a valid target, e.g. "37" or the first valid target
    target = VALID_PY_TARGETS[0]
    config_stdlib = _Config(py_version=target, known_standard_library=frozenset())
    assert config_stdlib.known_standard_library

    # 4. Test multi_line_output == WrapModes.VERTICAL_GRID_GROUPED_NO_COMMA
    config_wrap = _Config(multi_line_output=WrapModes.VERTICAL_GRID_GROUPED_NO_COMMA)
    assert config_wrap.multi_line_output == WrapModes.VERTICAL_GRID_GROUPED

    # 5. Test force_alphabetical_sort=True side effects
    config_alpha = _Config(force_alphabetical_sort=True)
    assert config_alpha.force_alphabetical_sort_within_sections is True
    assert config_alpha.no_sections is True
    assert config_alpha.lines_between_types == 1
    assert config_alpha.from_first is True

    # 6. Test wrap_length > line_length ValueError branch
    with pytest.raises(ValueError, match="wrap_length must be set lower than or equal to line_length"):
        _Config(wrap_length=100, line_length=50)
