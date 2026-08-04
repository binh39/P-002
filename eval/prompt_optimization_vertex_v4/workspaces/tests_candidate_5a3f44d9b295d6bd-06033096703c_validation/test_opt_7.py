# file: src\sample_repo\isort\isort\settings.py:820-910
# asked: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 843, 844, 845, 846, 847, 848, 850, 851, 852, 853, 855, 857, 858, 860, 861, 863, 864, 865, 866, 867, 869, 870, 872, 873, 875, 876, 877, 878, 880, 881, 882, 883, 886, 887, 888, 889, 890, 891, 892, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 834], [833, 843], [836, 837], [836, 843], [838, 839], [838, 841], [845, 846], [845, 860], [846, 847], [846, 857], [848, 845], [848, 849], [849, 848], [849, 855], [857, 845], [857, 858], [860, 861], [860, 910], [863, 864], [863, 886], [866, 867], [866, 869], [869, 870], [869, 872], [872, 873], [872, 875], [876, 877], [876, 880], [886, 887], [886, 910], [888, 889], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 895], [894, 896], [897, 898], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}
# gained: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 843, 844, 845, 846, 847, 848, 850, 857, 858, 860, 861, 863, 886, 887, 888, 889, 890, 891, 892, 894, 895, 896, 897, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 843], [845, 846], [845, 860], [846, 847], [846, 857], [848, 845], [848, 849], [849, 848], [857, 858], [860, 861], [863, 886], [886, 887], [886, 910], [888, 889], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 895], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}

import os
import pytest
from isort.settings import _get_config_data


def test_get_config_data_toml(tmp_path):
    toml_file = tmp_path / "pyproject.toml"
    toml_file.write_text(
        '[tool.isort]\nline_length = 88\n',
        encoding="utf-8",
    )
    res = _get_config_data(str(toml_file), ("tool.isort",))
    assert res["line_length"] == 88
    assert res["source"] == str(toml_file)






def test_get_config_data_various_types(tmp_path):
    ini_file = tmp_path / "setup.cfg"
    content = (
        "[isort]\n"
        "atomic = true\n"
        "force_grid_wrap = invalid\n"
        "comment_prefix = '#'\n"
        "known_third_party = requests\n"
        "sections = FUTURE,STDLIB,THIRDPARTY,FIRSTPARTY,LOCALFOLDER\n"
        "skip = setup.py\n"
    )
    ini_file.write_text(content, encoding="utf-8")
    res = _get_config_data(
        str(ini_file),
        (
            "isort",
            "*.{py}",
        ),
    )
    assert "atomic" in res
    assert "force_grid_wrap" in res
    assert "comment_prefix" in res
    assert "skip" in res
    assert "sections" in res
