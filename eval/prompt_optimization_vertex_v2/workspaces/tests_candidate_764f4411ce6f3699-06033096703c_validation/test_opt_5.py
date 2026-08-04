# file: src\sample_repo\isort\isort\settings.py:820-910
# asked: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 843, 844, 845, 846, 847, 848, 850, 851, 852, 853, 855, 857, 858, 860, 861, 863, 864, 865, 866, 867, 869, 870, 872, 873, 875, 876, 877, 878, 880, 881, 882, 883, 886, 887, 888, 889, 890, 891, 892, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 834], [833, 843], [836, 837], [836, 843], [838, 839], [838, 841], [845, 846], [845, 860], [846, 847], [846, 857], [848, 845], [848, 849], [849, 848], [849, 855], [857, 845], [857, 858], [860, 861], [860, 910], [863, 864], [863, 886], [866, 867], [866, 869], [869, 870], [869, 872], [872, 873], [872, 875], [876, 877], [876, 880], [886, 887], [886, 910], [888, 889], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 895], [894, 896], [897, 898], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}
# gained: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 843, 844, 845, 846, 857, 858, 860, 861, 863, 864, 865, 866, 867, 869, 870, 872, 873, 875, 876, 877, 878, 880, 881, 882, 883, 886, 887, 888, 890, 891, 892, 897, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 834], [833, 843], [836, 837], [838, 839], [838, 841], [845, 846], [845, 860], [846, 857], [857, 845], [857, 858], [860, 861], [860, 910], [863, 864], [863, 886], [866, 867], [866, 869], [869, 870], [869, 872], [872, 873], [872, 875], [876, 877], [876, 880], [886, 887], [886, 910], [888, 890], [890, 891], [890, 892], [892, 897], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}

import os
import tempfile
import pytest
from isort.settings import _get_config_data

def test_get_config_data_toml_nested_sections():
    toml_content = """
    [tool.isort]
    line_length = 100
    skip = ["venv"]
    [tool.isort.other]
    force_grid_wrap = 2
    """
    with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False, encoding="utf-8") as f:
        f.write(toml_content)
        temp_name = f.name

    try:
        data = _get_config_data(temp_name, ("tool.isort", "tool.isort.other"))
        assert data["line_length"] == 100
        assert data["skip"] == frozenset({"venv"})
        assert data["force_grid_wrap"] == 2
        assert data["source"] == temp_name
    finally:
        os.unlink(temp_name)

def test_editorconfig_various_indent_styles_and_max_line_length():
    editorconfig_content = """
root = true

[*.py]
indent_style = space
indent_size = 2
max_line_length = 100
comment_prefix = 'test#'
known_third_party = foo, bar

[*.js]
indent_style = tab
indent_size = tab
tab_width = 4
max_line_length = 120
force_grid_wrap = invalid_val
comment_prefix = "double"
"""
    with tempfile.NamedTemporaryFile("w", suffix=".editorconfig", delete=False, encoding="utf-8") as f:
        f.write(editorconfig_content)
        temp_name = f.name

    try:
        # Test space indent, finite line length, comment prefix with single quotes, and known_ prefix (abspaths)
        data_py = _get_config_data(temp_name, ("*.py",))
        assert data_py["indent"] == "  "
        assert data_py["line_length"] == 100
        assert data_py["comment_prefix"] == "test#"
        assert any("foo" in p for p in data_py["known_third_party"])

        # Test tab indent with tab_width, digit line length, force_grid_wrap fallback, and double quotes comment prefix
        data_js = _get_config_data(temp_name, ("*.js",))
        assert data_js["indent"] == "\t\t\t\t"
        assert data_js["line_length"] == 120
        assert data_js["force_grid_wrap"] == 2  # falls back to 2 when invalid and not "false"
        assert data_js["comment_prefix"] == "double"

        editorconfig_false = """
[*.py]
force_grid_wrap = false
"""
        with tempfile.NamedTemporaryFile("w", suffix=".editorconfig", delete=False, encoding="utf-8") as f2:
            f2.write(editorconfig_false)
            temp_name2 = f2.name
        try:
            data_false = _get_config_data(temp_name2, ("*.py",))
            assert data_false["force_grid_wrap"] == 0
        finally:
            os.unlink(temp_name2)

    finally:
        os.unlink(temp_name)


def test_get_config_data_empty_settings():
    content = """
[not_a_valid_section]
foo = bar
"""
    with tempfile.NamedTemporaryFile("w", suffix=".ini", delete=False, encoding="utf-8") as f:
        f.write(content)
        temp_name = f.name

    try:
        data = _get_config_data(temp_name, ("isort",))
        assert data == {}
    finally:
        os.unlink(temp_name)
