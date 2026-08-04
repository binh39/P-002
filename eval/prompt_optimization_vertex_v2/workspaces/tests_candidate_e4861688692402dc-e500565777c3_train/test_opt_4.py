# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 100]]}

from isort.settings import Config
from isort.sorting import section_key

def test_section_key_comprehensive():
    # 1. Test reverse_relative and startswith("from .") when sort_relative_in_force_sorted_sections is False
    config1 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
    )
    res1 = section_key("from .module import name", config1)
    assert res1.startswith("B")

    # 2. Test group_by_package and line.strip().startswith("from")
    config2 = Config(
        group_by_package=True,
    )
    res2 = section_key("from my_pkg import a, b", config2)
    assert "import" not in res2

    # 3. Test lexicographical sorting
    config3 = Config(
        lexicographical=True,
    )
    res3 = section_key("import os", config3)
    assert isinstance(res3, str)

    # 4. Test sort_relative_in_force_sorted_sections with reverse_relative=True and False
    config4a = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
    )
    res4a = section_key("from .module import name", config4a)

    config4b = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
    )
    res4b = section_key("from .module import name", config4b)
    assert res4a != res4b

    # 5. Test force_to_top matching section A
    config5 = Config(
        force_to_top=["module"],
    )
    res5 = section_key("module import something", config5)
    assert res5.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # Case A: len(split_module) > 1 (has " import ")
    config6a = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res6a = section_key("MyModule import Name", config6a)

    config6b = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res6b = section_key("MyModule import Name", config6b)

    # Case B: len(split_module) == 1 (no " import ", e.g., plain import line after removing "import ")
    config6c = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res6c = section_key("import MyModule", config6c)

    # 7. Test length_sort is True
    config7 = Config(
        length_sort=True,
    )
    res7 = section_key("import os", config7)
    assert len(res7) > 3
