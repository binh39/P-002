# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 98], [97, 100]]}

from isort.settings import Config
from isort.sorting import section_key


def test_section_key_branches():
    # 1. Test reverse_relative and line starts with "from ." (lines 61-68)
    config = Config(reverse_relative=True, sort_relative_in_force_sorted_sections=False)
    res = section_key("from .module import foo", config)
    assert res.startswith("B")

    # 2. Test group_by_package and line starts with "from" (lines 69-70)
    config = Config(group_by_package=True)
    res = section_key("from my_package.sub import foo", config)
    assert "import" not in res

    # 3. Test lexicographical=True (lines 72-73)
    config = Config(lexicographical=True)
    res = section_key("import os", config)
    assert isinstance(res, str)

    # 4. Test sort_relative_in_force_sorted_sections (lines 77-79)
    config = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=True)
    res = section_key("from ..module import foo", config)
    assert ".." in res

    config2 = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=False)
    res2 = section_key("from ..module import foo", config2)
    assert ".." in res2

    # 5. Test force_to_top (lines 80-81)
    config = Config(force_to_top=["module"])
    res = section_key("module import something", config)
    assert res.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections and case_sensitive != order_by_type (lines 86-96)
    # With len(split_module) > 1
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res = section_key("MyModule import Foo, Bar", config)
    assert "MyModule import" in res
    assert "foo" in res

    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("MyModule import Foo, Bar", config)
    assert "mymodule import" in res

    # Without split_module > 1 (len == 1) and not case_sensitive
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("MyModule", config)
    assert res == "BMymodule" or res.endswith("mymodule")

    # 7. Test elif not config.order_by_type (lines 97-98) when honor_case... is False
    config = Config(
        honor_case_in_force_sorted_sections=False,
        order_by_type=False,
    )
    res = section_key("MyModule import Foo", config)
    assert res == "Bmymodule import foo"

    # 8. Test length_sort=True (line 100)
    config = Config(length_sort=True)
    res = section_key("import os", config)
    # length of line after strip prefixes should be included
    assert len(res) > len("os") + 1
