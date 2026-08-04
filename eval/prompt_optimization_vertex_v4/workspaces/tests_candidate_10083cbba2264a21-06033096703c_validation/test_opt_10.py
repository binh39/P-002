# file: src\sample_repo\isort\isort\settings.py:820-910
# asked: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 843, 844, 845, 846, 847, 848, 850, 851, 852, 853, 855, 857, 858, 860, 861, 863, 864, 865, 866, 867, 869, 870, 872, 873, 875, 876, 877, 878, 880, 881, 882, 883, 886, 887, 888, 889, 890, 891, 892, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 834], [833, 843], [836, 837], [836, 843], [838, 839], [838, 841], [845, 846], [845, 860], [846, 847], [846, 857], [848, 845], [848, 849], [849, 848], [849, 855], [857, 845], [857, 858], [860, 861], [860, 910], [863, 864], [863, 886], [866, 867], [866, 869], [869, 870], [869, 872], [872, 873], [872, 875], [876, 877], [876, 880], [886, 887], [886, 910], [888, 889], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 895], [894, 896], [897, 898], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}
# gained: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 834, 835, 836, 837, 838, 839, 840, 843, 844, 845, 846, 857, 858, 860, 861, 863, 864, 865, 866, 867, 869, 872, 873, 875, 876, 877, 878, 880, 881, 882, 883, 886, 887, 888, 889, 890, 891, 892, 894, 896, 897, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 834], [833, 843], [836, 837], [838, 839], [845, 846], [845, 860], [846, 857], [857, 858], [860, 861], [863, 864], [863, 886], [866, 867], [869, 872], [872, 873], [876, 877], [886, 887], [886, 910], [888, 889], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 896], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}

import pytest
import os
from isort.settings import _get_config_data


def test_get_config_data_toml(tmp_path):
    toml_file = tmp_path / "pyproject.toml"
    toml_file.write_text(
        '[tool.isort]\n'
        'line_length = 88\n'
        'force_grid_wrap = "false"\n'
        'comment_prefix = "#"\n'
        'skip_glob = ["*.py"]\n'
        'known_third_party = ["requests"]\n'
        'sections = ["FUTURE", "STDLIB"]\n'
        'py_version = 38\n'
        'include_trailing_comma = true\n',
        encoding="utf-8"
    )
    res = _get_config_data(str(toml_file), ("tool.isort",))
    assert res["line_length"] == 88
    assert res["force_grid_wrap"] == 0
    assert res["comment_prefix"] == "#"
    assert "py_version" in res
    assert res["include_trailing_comma"] is True




def test_get_config_data_editorconfig_tab(tmp_path):
    editorconfig_file = tmp_path / ".editorconfig"
    editorconfig_file.write_text(
        '[*.py]\n'
        'indent_style = tab\n'
        'indent_size = tab\n'
        'tab_width = 2\n'
        'max_line_length = 120\n',
        encoding="utf-8"
    )
    res = _get_config_data(str(editorconfig_file), ("*.py",))
    assert res["indent"] == "\t\t"
    assert res["line_length"] == 120


def test_types_and_converters_coverage(tmp_path):
    ini_file = tmp_path / "setup.cfg"
    ini_file.write_text(
        '[isort]\n'
        'sections = FUTURE,STDLIB\n'
        'default_section = THIRDPARTY\n'
        'force_grid_wrap = invalid_val\n'
        'comment_prefix = "/*"\n'
        'skip = foo.py, bar.py\n'
        'line_length = 79\n',
        encoding="utf-8"
    )
    res = _get_config_data(str(ini_file), ("isort",))
    assert isinstance(res["sections"], tuple)
    assert res["force_grid_wrap"] == 2
    assert res["comment_prefix"] == "/*"
    assert res["line_length"] == 79
