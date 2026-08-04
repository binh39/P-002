# file: src\sample_repo\isort\isort\settings.py:820-910
# asked: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 843, 844, 845, 846, 847, 848, 850, 851, 852, 853, 855, 857, 858, 860, 861, 863, 864, 865, 866, 867, 869, 870, 872, 873, 875, 876, 877, 878, 880, 881, 882, 883, 886, 887, 888, 889, 890, 891, 892, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 834], [833, 843], [836, 837], [836, 843], [838, 839], [838, 841], [845, 846], [845, 860], [846, 847], [846, 857], [848, 845], [848, 849], [849, 848], [849, 855], [857, 845], [857, 858], [860, 861], [860, 910], [863, 864], [863, 886], [866, 867], [866, 869], [869, 870], [869, 872], [872, 873], [872, 875], [876, 877], [876, 880], [886, 887], [886, 910], [888, 889], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 895], [894, 896], [897, 898], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}
# gained: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 843, 844, 845, 846, 857, 858, 860, 861, 863, 864, 865, 866, 869, 872, 873, 875, 876, 877, 878, 880, 881, 882, 883, 886, 887, 888, 890, 891, 892, 897, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 834], [833, 843], [836, 837], [838, 839], [838, 841], [845, 846], [845, 860], [846, 857], [857, 858], [860, 861], [863, 864], [863, 886], [866, 869], [869, 872], [872, 873], [876, 877], [886, 887], [886, 910], [888, 890], [890, 891], [890, 892], [892, 897], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}

import os
import tempfile
import pytest
from isort.settings import _get_config_data

def test_get_config_data_toml():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "pyproject.toml")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(
                "[tool.isort]\n"
                "line_length = 120\n"
                "force_grid_wrap = 'invalid'\n"
                "comment_prefix = '\"foo\"'\n"
                "known_third_party = ['requests']\n"
            )
        data = _get_config_data(config_path, ("tool.isort",))
        assert data["line_length"] == 120
        assert data["comment_prefix"] == "foo"
        assert data["source"] == config_path


def test_get_config_data_editorconfig_tab_indent_and_tuple_frozenset():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, ".editorconfig")
        content = (
            "# some comment\n"
            "[*.py]\n"
            "indent_style = tab\n"
            "indent_size = 3\n"
            "max_line_length = 100\n"
            "force_grid_wrap = true\n"
            "skip = a, b\n"
        )
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)

        data = _get_config_data(config_path, ("*.py",))
        assert data["indent"] == "\t\t\t"
        assert data["line_length"] == 100
        assert data["force_grid_wrap"] == 2
        assert isinstance(data["skip"], frozenset)
        assert "a" in data["skip"]
        assert "b" in data["skip"]

def test_get_config_data_ini_section_and_converters():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, ".isort.cfg")
        content = (
            "[isort]\n"
            "line_length = 88\n"
            "force_grid_wrap = invalid_val\n"
            "skip = file1.py, file2.py\n"
        )
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)

        data = _get_config_data(config_path, ("isort",))
        assert data["line_length"] == 88
        assert data["force_grid_wrap"] == 2
        assert isinstance(data["skip"], frozenset)
