# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

from isort.settings import Config
from isort.sorting import section_key


def test_section_key_full_coverage():
    # 1. Test reverse_relative and line starts with "from ."
    config_rev = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
    )
    res1 = section_key("from .module import name", config_rev)
    assert res1.startswith("B")

    # 2. Test group_by_package and line starts with "from"
    config_group = Config(group_by_package=True)
    res2 = section_key("from os import path", config_group)
    assert "import" not in res2

    # 3. Test lexicographical=True
    config_lex = Config(lexicographical=True)
    res3 = section_key("import os", config_lex)
    assert isinstance(res3, str)

    # 4. Test sort_relative_in_force_sorted_sections=True with reverse_relative=True and False
    config_sort_rel_1 = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
    )
    res4_1 = section_key("from .module import name", config_sort_rel_1)
    assert res4_1.startswith("B")

    config_sort_rel_2 = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
    )
    res4_2 = section_key("from .module import name", config_sort_rel_2)
    assert res4_2.startswith("B")

    # 5. Test force_to_top triggering section = "A"
    config_force = Config(force_to_top=["os"])
    res5 = section_key("import os", config_force)
    assert res5.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # Case A: split_module > 1, case_sensitive=False, order_by_type=True
    config_honor_1 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res6_1 = section_key("OS import Name", config_honor_1)
    assert "os import Name" in res6_1

    # Case B: split_module > 1, case_sensitive=True, order_by_type=False
    config_honor_2 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res6_2 = section_key("OS import Name", config_honor_2)
    assert "OS import name" in res6_2

    # Case C: split_module <= 1 (no import), case_sensitive=False
    config_honor_3 = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res6_3 = section_key("OSMODULE", config_honor_3)
    assert "osmodule" in res6_3

    # 7. Test `elif not config.order_by_type:` branch (honor_case_in_force_sorted_sections is False, order_by_type=False)
    config_order_type = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    res7 = section_key("OS import Name", config_order_type)
    assert res7 == "Bos import name"

    # 8. Test length_sort=True
    config_len_sort = Config(length_sort=True)
    res8 = section_key("os", config_len_sort)
    assert "2" in res8
