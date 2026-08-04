# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

from isort.settings import Config
from isort.sorting import section_key


def test_section_key_coverage_full():
    # 1. Test reverse_relative + line.startswith("from .") without sort_relative_in_force_sorted_sections
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
        group_by_package=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
        length_sort=False,
    )
    res = section_key("from .module import name", config)
    assert res == "B. module import name"

    # 2. Test group_by_package with "from"
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=True,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
        length_sort=False,
    )
    res = section_key("from pkg import name", config)
    assert res == "Bpkg"

    # 3. Test lexicographical=True
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=True,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
        length_sort=False,
    )
    res = section_key("import os", config)
    assert "os" in res

    # 4. Test sort_relative_in_force_sorted_sections=True with reverse_relative=True and False
    config_sort_rel_rev = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
        group_by_package=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
        length_sort=False,
    )
    res1 = section_key("from ..mod import x", config_sort_rel_rev)
    assert ".." in res1

    config_sort_rel_no_rev = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
        length_sort=False,
    )
    res2 = section_key("from ..mod import x", config_sort_rel_no_rev)
    assert ".." in res2

    # 5. Test force_to_top matches line.split(" ")[0] -> section = "A"
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        force_to_top=("os",),
        honor_case_in_force_sorted_sections=False,
        order_by_type=True,
        length_sort=False,
    )
    res = section_key("os", config)
    assert res.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # Case A: len(split_module) > 1, case_sensitive=False, order_by_type=True
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
        length_sort=False,
    )
    res = section_key("ModuleA import NamesB", config)
    assert "modulea import NamesB" in res

    # Case B: len(split_module) > 1, case_sensitive=True, order_by_type=False
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
        length_sort=False,
    )
    res = section_key("ModuleA import NamesB", config)
    assert "ModuleA import namesb" in res

    # Case C: len(split_module) <= 1, case_sensitive=False
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
        length_sort=False,
    )
    res = section_key("ModuleWithoutImport", config)
    assert res == "Bmodulewithoutimport"

    # 7. Test elif not config.order_by_type (when honor_case is False, order_by_type is False)
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        case_sensitive=False,
        order_by_type=False,
        length_sort=False,
    )
    res = section_key("SomeLine", config)
    assert res == "Bsomeline"

    # 8. Test length_sort = True
    config = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=False,
        group_by_package=False,
        lexicographical=False,
        force_to_top=(),
        honor_case_in_force_sorted_sections=False,
        case_sensitive=True,
        order_by_type=True,
        length_sort=True,
    )
    res = section_key("abc", config)
    assert res.startswith("B3")
