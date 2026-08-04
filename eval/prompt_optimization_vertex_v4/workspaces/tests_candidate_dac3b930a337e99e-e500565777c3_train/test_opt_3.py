# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

from isort.settings import Config
from isort.sorting import section_key


def test_section_key_coverage():
    # 1. Test reverse_relative and line starting with "from ."
    config1 = Config(
        sort_relative_in_force_sorted_sections=False,
        reverse_relative=True,
    )
    res1 = section_key("from .module import foo", config1)
    assert res1.startswith("B")

    # 2. Test group_by_package and line starting with "from"
    config2 = Config(
        group_by_package=True,
    )
    res2 = section_key("from os import path", config2)
    assert "import" not in res2

    # 3. Test lexicographical
    config3 = Config(
        lexicographical=True,
    )
    res3 = section_key("import os", config3)
    assert isinstance(res3, str)

    # 4. Test sort_relative_in_force_sorted_sections with reverse_relative=True vs False
    config4a = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=True,
    )
    res4a = section_key("from ..foo import bar", config4a)
    assert isinstance(res4a, str)

    config4b = Config(
        sort_relative_in_force_sorted_sections=True,
        reverse_relative=False,
    )
    res4b = section_key("from ..foo import bar", config4b)
    assert isinstance(res4b, str)

    # 5. Test force_to_top (section = "A")
    config5 = Config(
        force_to_top=["sys"],
    )
    res5 = section_key("import sys", config5)
    assert res5.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type
    # case_sensitive = False, order_by_type = True
    config6a = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res6a = section_key("ModuleA import NamesB", config6a)
    assert "modulea" in res6a

    # case_sensitive = True, order_by_type = False (with import and without import, length_sort=True)
    config6b = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
        length_sort=True,
    )
    res6b = section_key("ModuleA import NamesB", config6b)
    assert "namesb" in res6b

    config6c = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res6c = section_key("ModuleANoImport", config6c)
    assert "moduleanoimport" in res6c

    # 7. Test elif not config.order_by_type (when honor_case_in_force_sorted_sections is False)
    config7 = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    res7 = section_key("SomeModule", config7)
    assert res7.startswith("B")
    assert "somemodule" in res7
