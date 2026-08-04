# file: src\sample_repo\isort\isort\settings.py:820-910
# asked: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 843, 844, 845, 846, 847, 848, 850, 851, 852, 853, 855, 857, 858, 860, 861, 863, 864, 865, 866, 867, 869, 870, 872, 873, 875, 876, 877, 878, 880, 881, 882, 883, 886, 887, 888, 889, 890, 891, 892, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 834], [833, 843], [836, 837], [836, 843], [838, 839], [838, 841], [845, 846], [845, 860], [846, 847], [846, 857], [848, 845], [848, 849], [849, 848], [849, 855], [857, 845], [857, 858], [860, 861], [860, 910], [863, 864], [863, 886], [866, 867], [866, 869], [869, 870], [869, 872], [872, 873], [872, 875], [876, 877], [876, 880], [886, 887], [886, 910], [888, 889], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 895], [894, 896], [897, 898], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}
# gained: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 843, 844, 845, 846, 857, 858, 860, 861, 863, 886, 887, 888, 890, 891, 892, 894, 895, 896, 897, 899, 905, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 843], [845, 846], [845, 860], [846, 857], [857, 858], [860, 861], [863, 886], [886, 887], [886, 910], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 895], [897, 899], [899, 905], [905, 908]]}

import os
import tempfile
import pytest
from isort.settings import _get_config_data

def test_get_config_data_toml_nested_sections():
    toml_content = """
    [tool.isort]
    line_length = 100
    skip = ["venv"]
    [tool.other]
    line_length = 50
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False, encoding="utf-8") as f:
        f.write(toml_content)
        temp_path = f.name

    try:
        data = _get_config_data(temp_path, ("tool.isort",))
        assert data["line_length"] == 100
        assert data["source"] == temp_path
    finally:
        os.remove(temp_path)



def test_get_config_data_ini_types_and_converters():
    ini_content = """
    [settings]
    line_length = 88
    force_to_top = os, sys
    skip_gitignore = true
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False, encoding="utf-8") as f:
        f.write(ini_content)
        temp_path = f.name

    try:
        data = _get_config_data(temp_path, ("settings",))
        assert data["line_length"] == 88
        assert isinstance(data["force_to_top"], frozenset)
        assert "os" in data["force_to_top"]
        assert data["skip_gitignore"] is True
    finally:
        os.remove(temp_path)
