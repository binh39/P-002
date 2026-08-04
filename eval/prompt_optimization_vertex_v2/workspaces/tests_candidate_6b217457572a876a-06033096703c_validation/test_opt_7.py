# file: src\sample_repo\isort\isort\settings.py:820-910
# asked: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 843, 844, 845, 846, 847, 848, 850, 851, 852, 853, 855, 857, 858, 860, 861, 863, 864, 865, 866, 867, 869, 870, 872, 873, 875, 876, 877, 878, 880, 881, 882, 883, 886, 887, 888, 889, 890, 891, 892, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 834], [833, 843], [836, 837], [836, 843], [838, 839], [838, 841], [845, 846], [845, 860], [846, 847], [846, 857], [848, 845], [848, 849], [849, 848], [849, 855], [857, 845], [857, 858], [860, 861], [860, 910], [863, 864], [863, 886], [866, 867], [866, 869], [869, 870], [869, 872], [872, 873], [872, 875], [876, 877], [876, 880], [886, 887], [886, 910], [888, 889], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 895], [894, 896], [897, 898], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}
# gained: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 843, 844, 845, 846, 857, 858, 860, 861, 863, 886, 887, 888, 889, 890, 891, 892, 894, 895, 896, 897, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 843], [845, 846], [845, 860], [846, 857], [857, 858], [860, 861], [863, 886], [886, 887], [886, 910], [888, 889], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 895], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}

import os
import tempfile
import pytest
from isort.settings import _get_config_data


@pytest.fixture
def custom_tmp_path():
    d = tempfile.mkdtemp()
    yield d
    # Clean up files inside and directory itself
    for root, dirs, files in os.walk(d, topdown=False):
        for name in files:
            try:
                os.unlink(os.path.join(root, name))
            except Exception:
                pass
        for name in dirs:
            try:
                os.rmdir(os.path.join(root, name))
            except Exception:
                pass
    try:
        os.rmdir(d)
    except Exception:
        pass


def test_get_config_data_toml(custom_tmp_path):
    toml_path = os.path.join(custom_tmp_path, "pyproject.toml")
    with open(toml_path, "w", encoding="utf-8") as f:
        f.write('[tool.isort]\nline_length = 88\n')
    res = _get_config_data(toml_path, ("tool.isort",))
    assert res["line_length"] == 88
    assert res["source"] == toml_path






def test_get_config_data_ini_various_types(custom_tmp_path):
    ini_path = os.path.join(custom_tmp_path, "setup.cfg")
    with open(ini_path, "w", encoding="utf-8") as f:
        f.write(
            "[isort]\n"
            "atomic = true\n"
            "force_grid_wrap = invalid\n"
            "comment_prefix = \"#\"\n"
            "known_first_party = foo,bar\n"
            "src_paths = a,b\n"
        )
    res = _get_config_data(ini_path, ("isort",))
    assert res.get("atomic") is True
    assert res.get("force_grid_wrap") == 2
    assert res.get("comment_prefix") == "#"
    assert "foo" in res.get("known_first_party")
    assert res["source"] == ini_path


def test_get_config_data_ini_frozenset_and_tuple(custom_tmp_path):
    ini_path = os.path.join(custom_tmp_path, "setup.cfg")
    with open(ini_path, "w", encoding="utf-8") as f:
        f.write(
            "[isort]\n"
            "skip = file1.py,file2.py\n"
            "only_sections = true\n"
        )
    res = _get_config_data(ini_path, ("isort",))
    assert isinstance(res.get("skip"), (tuple, frozenset, list))
    assert res["source"] == ini_path
