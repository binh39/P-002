# file: src\sample_repo\isort\isort\settings.py:820-910
# asked: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 843, 844, 845, 846, 847, 848, 850, 851, 852, 853, 855, 857, 858, 860, 861, 863, 864, 865, 866, 867, 869, 870, 872, 873, 875, 876, 877, 878, 880, 881, 882, 883, 886, 887, 888, 889, 890, 891, 892, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 834], [833, 843], [836, 837], [836, 843], [838, 839], [838, 841], [845, 846], [845, 860], [846, 847], [846, 857], [848, 845], [848, 849], [849, 848], [849, 855], [857, 845], [857, 858], [860, 861], [860, 910], [863, 864], [863, 886], [866, 867], [866, 869], [869, 870], [869, 872], [872, 873], [872, 875], [876, 877], [876, 880], [886, 887], [886, 910], [888, 889], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 895], [894, 896], [897, 898], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}
# gained: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 843, 844, 845, 846, 857, 858, 860, 861, 863, 886, 887, 888, 889, 890, 891, 892, 894, 895, 896, 897, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 843], [845, 846], [845, 860], [846, 857], [857, 858], [860, 861], [863, 886], [886, 887], [886, 910], [888, 889], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 895], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}

import os
import tempfile
import pytest
from isort.settings import _get_config_data


def test_get_config_data_toml_nested_sections():
    toml_content = """
    [tool.isort]
    line_length = 100
    force_grid_wrap = "false"
    comment_prefix = "'# custom'"
    known_third_party = ["requests", "pydantic"]

    [tool.other]
    line_length = 50
    """
    with tempfile.NamedTemporaryFile("wb", suffix=".toml", delete=False) as tf:
        tf.write(toml_content.encode("utf-8"))
        tf_name = tf.name

    try:
        data = _get_config_data(tf_name, ("tool.isort",))
        assert data["line_length"] == 100
        assert data["force_grid_wrap"] == 0
        assert data["comment_prefix"] == "# custom"
        assert "requests" in data["known_third_party"]
        assert data["source"] == tf_name
    finally:
        os.unlink(tf_name)




def test_get_config_data_ini_types_and_fallbacks():
    ini_content = """
[isort]
line_length = 111
force_grid_wrap = false
atomic = False
forced_separate = a, b
known_first_party = my_app
comment_prefix = 'single'
    """
    with tempfile.NamedTemporaryFile("w", suffix=".ini", encoding="utf-8", delete=False) as tf:
        tf.write(ini_content)
        tf_name = tf.name

    try:
        data = _get_config_data(tf_name, ("isort",))
        assert data["line_length"] == 111
        assert data["atomic"] is False
        assert data["force_grid_wrap"] == 0
        assert data["forced_separate"] == ("a", "b")
        assert "my_app" in data["known_first_party"]
        assert data["comment_prefix"] == "single"
        assert data["source"] == tf_name
    finally:
        os.unlink(tf_name)
