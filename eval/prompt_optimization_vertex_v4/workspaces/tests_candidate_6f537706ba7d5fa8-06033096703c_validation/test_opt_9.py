# file: src\sample_repo\isort\isort\settings.py:820-910
# asked: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 843, 844, 845, 846, 847, 848, 850, 851, 852, 853, 855, 857, 858, 860, 861, 863, 864, 865, 866, 867, 869, 870, 872, 873, 875, 876, 877, 878, 880, 881, 882, 883, 886, 887, 888, 889, 890, 891, 892, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 834], [833, 843], [836, 837], [836, 843], [838, 839], [838, 841], [845, 846], [845, 860], [846, 847], [846, 857], [848, 845], [848, 849], [849, 848], [849, 855], [857, 845], [857, 858], [860, 861], [860, 910], [863, 864], [863, 886], [866, 867], [866, 869], [869, 870], [869, 872], [872, 873], [872, 875], [876, 877], [876, 880], [886, 887], [886, 910], [888, 889], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 895], [894, 896], [897, 898], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}
# gained: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 843, 844, 845, 846, 847, 848, 850, 851, 852, 853, 855, 857, 858, 860, 861, 863, 864, 865, 866, 869, 870, 875, 876, 877, 878, 880, 881, 882, 883, 886, 887, 888, 889, 890, 891, 892, 894, 895, 896, 897, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 834], [833, 843], [836, 837], [838, 839], [838, 841], [845, 846], [845, 860], [846, 847], [846, 857], [848, 845], [848, 849], [849, 848], [849, 855], [857, 858], [860, 861], [863, 864], [863, 886], [866, 869], [869, 870], [876, 877], [886, 887], [886, 910], [888, 889], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 895], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}

import os
import pytest
from isort.settings import _get_config_data


def test_get_config_data_toml(tmp_path):
    toml_file = tmp_path / "pyproject.toml"
    toml_file.write_text(
        '[tool.isort]\nline_length = 88\nknown_third_party = ["foo", "bar"]\n'
    )
    res = _get_config_data(str(toml_file), ("tool.isort",))
    assert res["line_length"] == 88
    assert res["source"] == str(toml_file)


def test_get_config_data_editorconfig_space_indent(tmp_path):
    editorconfig_file = tmp_path / ".editorconfig"
    editorconfig_file.write_text(
        "root = true\n\n[*.{py}]\nindent_style = space\nindent_size = 4\nmax_line_length = 100\nline_length = 100\n"
    )
    res = _get_config_data(str(editorconfig_file), ("*.{py}",))
    assert res["indent"] == "    "
    assert res["line_length"] == 100




def test_get_config_data_converters_and_types(tmp_path):
    ini_file = tmp_path / "setup.cfg"
    ini_file.write_text(
        "[isort]\n"
        "atomic = true\n"
        "sections = FUTURE,STDLIB,THIRDPARTY\n"
        "known_first_party = my_module\n"
        "force_grid_wrap = false\n"
        "comment_prefix = '#'\n"
        "line_length = 79\n"
    )
    res = _get_config_data(str(ini_file), ("isort",))
    assert res["atomic"] is True
    assert isinstance(res["sections"], tuple)
    assert isinstance(res["known_first_party"], frozenset)
    assert res["force_grid_wrap"] == 0
    assert res["comment_prefix"] == "#"


def test_get_config_data_force_grid_wrap_invalid(tmp_path):
    ini_file = tmp_path / "setup.cfg"
    ini_file.write_text(
        "[isort]\n"
        "force_grid_wrap = invalid_val\n"
        "line_length = 79\n"
    )
    res = _get_config_data(str(ini_file), ("isort",))
    assert res["force_grid_wrap"] == 2


def test_get_config_data_frozenset_and_bool_conversion(tmp_path):
    ini_file = tmp_path / "setup.cfg"
    ini_file.write_text(
        "[isort]\n"
        "balanced_wrapping = yes\n"
        "skip = file1.py,file2.py\n"
        "line_length = 79\n"
    )
    res = _get_config_data(str(ini_file), ("isort",))
    assert isinstance(res["skip"], frozenset)
    assert res["balanced_wrapping"] is True
