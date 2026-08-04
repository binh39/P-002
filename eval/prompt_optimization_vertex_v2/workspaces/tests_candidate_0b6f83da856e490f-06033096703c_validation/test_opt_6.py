# file: src\sample_repo\isort\isort\settings.py:820-910
# asked: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 843, 844, 845, 846, 847, 848, 850, 851, 852, 853, 855, 857, 858, 860, 861, 863, 864, 865, 866, 867, 869, 870, 872, 873, 875, 876, 877, 878, 880, 881, 882, 883, 886, 887, 888, 889, 890, 891, 892, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 834], [833, 843], [836, 837], [836, 843], [838, 839], [838, 841], [845, 846], [845, 860], [846, 847], [846, 857], [848, 845], [848, 849], [849, 848], [849, 855], [857, 845], [857, 858], [860, 861], [860, 910], [863, 864], [863, 886], [866, 867], [866, 869], [869, 870], [869, 872], [872, 873], [872, 875], [876, 877], [876, 880], [886, 887], [886, 910], [888, 889], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 895], [894, 896], [897, 898], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}
# gained: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 843, 844, 845, 846, 857, 858, 860, 861, 863, 864, 865, 866, 867, 869, 870, 872, 873, 875, 876, 877, 878, 880, 881, 882, 883, 886, 887, 888, 889, 890, 891, 892, 897, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 834], [833, 843], [836, 837], [838, 839], [838, 841], [845, 846], [845, 860], [846, 857], [857, 858], [860, 861], [863, 864], [863, 886], [866, 867], [866, 869], [869, 870], [869, 872], [872, 873], [876, 877], [886, 887], [886, 910], [888, 889], [888, 890], [890, 891], [890, 892], [892, 897], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}

import os
import tempfile
import pytest
from isort.settings import _get_config_data


def test_get_config_data_toml():
    with tempfile.TemporaryDirectory() as tmpdir:
        toml_file = os.path.join(tmpdir, "pyproject.toml")
        with open(toml_file, "w", encoding="utf-8") as f:
            f.write('[tool.isort]\nline_length = 88\n')
        result = _get_config_data(toml_file, ("tool.isort",))
        assert result["line_length"] == 88
        assert result["source"] == toml_file


def test_get_config_data_editorconfig():
    with tempfile.TemporaryDirectory() as tmpdir:
        ec_file = os.path.join(tmpdir, ".editorconfig")
        ec_content = """
root = true

[*.py]
indent_style = space
indent_size = 4
max_line_length = 100
line_length = 120
known_first_party = my_pkg
"""
        with open(ec_file, "w", encoding="utf-8") as f:
            f.write(ec_content.strip())
        result = _get_config_data(ec_file, ("*.py",))
        assert result["source"] == ec_file
        assert result["indent"] == "    "
        assert result["line_length"] == 100


def test_get_config_data_editorconfig_tab_and_off():
    with tempfile.TemporaryDirectory() as tmpdir:
        ec_file = os.path.join(tmpdir, ".editorconfig")
        ec_content = """
root = true

[*.py]
indent_style = tab
indent_size = tab
tab_width = 2
max_line_length = 120
"""
        with open(ec_file, "w", encoding="utf-8") as f:
            f.write(ec_content.strip())
        result = _get_config_data(ec_file, ("*.py",))
        assert result["indent"] == "\t\t"
        assert result["line_length"] == 120


def test_get_config_data_types_conversion():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_file = os.path.join(tmpdir, ".isort.cfg")
        cfg_content = """
[isort]
line_length = 79
force_grid_wrap = false
comment_prefix = "#"
sections = FUTURE,STDLIB,THIRDPARTY,FIRSTPARTY,LOCALFOLDER
known_third_party = requests
skip = setup.py
"""
        with open(cfg_file, "w", encoding="utf-8") as f:
            f.write(ec_content_str := cfg_content.strip())
        result = _get_config_data(cfg_file, ("isort",))
        assert result["line_length"] == 79
        assert result["force_grid_wrap"] == 0
        assert result["comment_prefix"] == "#"
        assert isinstance(result["sections"], tuple)
        assert isinstance(result["skip"], frozenset)
        assert isinstance(result["known_third_party"], frozenset)


def test_get_config_data_force_grid_wrap_value_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_file = os.path.join(tmpdir, ".isort.cfg")
        cfg_content = """
[isort]
force_grid_wrap = invalid_bool_or_int
"""
        with open(cfg_file, "w", encoding="utf-8") as f:
            f.write(cfg_content.strip())
        result = _get_config_data(cfg_file, ("isort",))
        assert result["force_grid_wrap"] == 2
