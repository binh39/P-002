# file: src\sample_repo\isort\isort\settings.py:820-910
# asked: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 843, 844, 845, 846, 847, 848, 850, 851, 852, 853, 855, 857, 858, 860, 861, 863, 864, 865, 866, 867, 869, 870, 872, 873, 875, 876, 877, 878, 880, 881, 882, 883, 886, 887, 888, 889, 890, 891, 892, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 834], [833, 843], [836, 837], [836, 843], [838, 839], [838, 841], [845, 846], [845, 860], [846, 847], [846, 857], [848, 845], [848, 849], [849, 848], [849, 855], [857, 845], [857, 858], [860, 861], [860, 910], [863, 864], [863, 886], [866, 867], [866, 869], [869, 870], [869, 872], [872, 873], [872, 875], [876, 877], [876, 880], [886, 887], [886, 910], [888, 889], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 895], [894, 896], [897, 898], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}
# gained: {"lines": [820, 821, 823, 824, 825, 826, 827, 828, 829, 830, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 843, 844, 845, 846, 847, 848, 850, 851, 852, 853, 855, 857, 858, 860, 861, 863, 864, 865, 866, 867, 869, 870, 872, 873, 875, 876, 877, 878, 880, 881, 882, 883, 886, 887, 888, 890, 891, 892, 894, 895, 896, 897, 899, 900, 901, 902, 903, 904, 905, 906, 908, 910], "branches": [[823, 824], [823, 832], [826, 827], [826, 860], [828, 829], [828, 830], [833, 834], [833, 843], [836, 837], [838, 839], [838, 841], [845, 846], [845, 860], [846, 847], [846, 857], [848, 845], [848, 849], [849, 848], [849, 855], [857, 858], [860, 861], [863, 864], [863, 886], [866, 867], [866, 869], [869, 870], [869, 872], [872, 873], [876, 877], [876, 880], [886, 887], [886, 910], [888, 890], [890, 891], [890, 892], [892, 894], [892, 897], [894, 895], [894, 896], [897, 899], [899, 900], [899, 905], [905, 906], [905, 908]]}

import os
import tempfile
import pytest
from isort.settings import _get_config_data


def test_get_config_data_comprehensive_coverage():
    content = """
[isort]
force_sort_within_sections = true
skip = foo, bar
skip_glob = baz
known_third_party = my_third_party
force_grid_wrap = false
comment_prefix = '#'
line_length = 79
indent_style = space
indent_size = 4
max_line_length = off
"""

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".cfg", encoding="utf-8") as tf:
        tf.write(content)
        tf_name = tf.name

    try:
        settings = _get_config_data(tf_name, ("isort",))
        assert settings.get("force_sort_within_sections") is True
        assert "foo" in settings.get("skip", ())
        assert settings.get("line_length") == 79
    finally:
        if os.path.exists(tf_name):
            os.remove(tf_name)

    editorconfig_content = """
[*.{py,pyw}]
indent_style = tab
indent_size = tab
tab_width = 2
max_line_length = 88
force_grid_wrap = true
comment_prefix = "//"
known_first_party = my_app
include_trailing_comma = yes
"""

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".editorconfig", encoding="utf-8") as tf:
        tf.write(editorconfig_content)
        tf_name = tf.name

    try:
        settings = _get_config_data(tf_name, ("*.{py}",))
        assert settings.get("indent") == "\t\t"
        assert settings.get("line_length") == 88
        assert settings.get("force_grid_wrap") == 2
    finally:
        if os.path.exists(tf_name):
            os.remove(tf_name)

    editorconfig_false = """
[*.py]
force_grid_wrap = false
indent_style = space
indent_size = 2
"""
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".editorconfig", encoding="utf-8") as tf:
        tf.write(editorconfig_false)
        tf_name = tf.name

    try:
        settings = _get_config_data(tf_name, ("*.py",))
        assert settings.get("force_grid_wrap") == 0
        assert settings.get("indent") == "  "
    finally:
        if os.path.exists(tf_name):
            os.remove(tf_name)

    # Test TOML config parsing branch
    toml_content = """
[isort]
force_sort_within_sections = true
line_length = 100
"""
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".toml", encoding="utf-8") as tf:
        tf.write(toml_content)
        tf_name = tf.name

    try:
        settings = _get_config_data(tf_name, ("isort",))
        assert settings.get("line_length") == 100
        assert settings.get("force_sort_within_sections") is True
    finally:
        if os.path.exists(tf_name):
            os.remove(tf_name)
