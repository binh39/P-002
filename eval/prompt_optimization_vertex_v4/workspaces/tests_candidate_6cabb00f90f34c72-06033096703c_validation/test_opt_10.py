# file: src\sample_repo\isort\isort\settings.py:820-910
# asked: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 843, 844, 845, 846, 847, 848, 850, 851, 852, 853, 855, 857, 858, 860, 861, 863, 864, 865, 866, 867, 869, 870, 872, 873, 875, 876, 877, 878, 880, 881, 882, 883, 886, 887, 888, 889, 890, 891, 892, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 834], [833, 843], [836, 837], [836, 843], [838, 839], [838, 841], [845, 846], [845, 860], [846, 847], [846, 857], [848, 845], [848, 849], [849, 848], [849, 855], [857, 845], [857, 858], [860, 861], [860, 910], [863, 864], [863, 886], [866, 867], [866, 869], [869, 870], [869, 872], [872, 873], [872, 875], [876, 877], [876, 880], [886, 887], [886, 910], [888, 889], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 895], [894, 896], [897, 898], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}
# gained: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 843, 844, 845, 846, 847, 848, 850, 851, 852, 853, 855, 857, 858, 860, 861, 863, 864, 865, 866, 867, 869, 872, 873, 875, 876, 880, 881, 882, 883, 886, 887, 888, 890, 891, 892, 894, 895, 896, 897, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 834], [833, 843], [836, 837], [838, 839], [838, 841], [845, 846], [845, 860], [846, 847], [846, 857], [848, 845], [848, 849], [849, 848], [849, 855], [857, 858], [860, 861], [863, 864], [863, 886], [866, 867], [869, 872], [872, 873], [876, 880], [886, 887], [886, 910], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 895], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}

import os
import pytest
from isort.settings import _get_config_data


def test_get_config_data_toml_and_various_types(tmp_path):
    toml_file = tmp_path / "pyproject.toml"
    toml_file.write_text(
        """
[tool.isort]
line_length = 120
skip = ["foo.py", "bar.py"]
skip_glob = "baz_*"
skip_gitignore = "true"
known_third_party = ["requests"]
force_grid_wrap = "false"
comment_prefix = '"custom_comment#"'
indent_style = "space"
indent_size = "2"
""",
        encoding="utf-8",
    )

    settings = _get_config_data(str(toml_file), ("tool.isort",))
    assert settings["line_length"] == 120
    assert settings["skip"] == frozenset(("foo.py", "bar.py"))
    assert settings["skip_glob"] == frozenset({"baz_*"})
    assert settings["skip_gitignore"] is True
    assert settings["known_third_party"] == frozenset({"requests"})
    assert settings["force_grid_wrap"] == 0
    assert settings["comment_prefix"] == "custom_comment#"


def test_get_config_data_editorconfig_variants(tmp_path):
    editorconfig_file = tmp_path / ".editorconfig"
    editorconfig_file.write_text(
        """
root = true

[*.{py,pyi}]
indent_style = tab
indent_size = tab
tab_width = 4
line_length = 79
skip = a.py, b.py
""",
        encoding="utf-8",
    )

    settings = _get_config_data(str(editorconfig_file), ("*.{py}",))
    assert settings["indent"] == "\t" * 4
    assert settings["skip"] == frozenset(("a.py", "b.py"))


def test_get_config_data_ini_force_grid_wrap_ValueError_and_frozenset(tmp_path):
    ini_file = tmp_path / ".isort.cfg"
    ini_file.write_text(
        """
[settings]
force_grid_wrap = invalid_val
extend_skip = x.py, y.py
""",
        encoding="utf-8",
    )

    settings = _get_config_data(str(ini_file), ("settings",))
    assert settings["force_grid_wrap"] == 2
    assert settings["extend_skip"] == frozenset({"x.py", "y.py"})


