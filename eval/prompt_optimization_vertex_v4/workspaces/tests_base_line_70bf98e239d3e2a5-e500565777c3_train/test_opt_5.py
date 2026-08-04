# file: src\sample_repo\isort\isort\sorting.py:58-100
# asked: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 100], "branches": [[61, 66], [61, 69], [67, 68], [67, 69], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [95, 100], [97, 98], [97, 100]]}
# gained: {"lines": [58, 59, 62, 63, 64, 66, 67, 68, 69, 70, 72, 73, 75, 76, 77, 78, 79, 80, 81, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 100], "branches": [[61, 66], [61, 69], [67, 68], [69, 70], [69, 72], [72, 73], [72, 75], [77, 78], [77, 80], [80, 81], [80, 86], [86, 87], [86, 97], [88, 89], [88, 95], [90, 91], [90, 92], [92, 93], [92, 94], [95, 96], [97, 100]]}

from isort.settings import Config
from isort.sorting import section_key


def test_section_key_branches():
    # 1. Test sort_relative_in_force_sorted_sections = False, reverse_relative = True, line starts with "from ."
    config = Config(reverse_relative=True, sort_relative_in_force_sorted_sections=False)
    res = section_key("from .foo import bar", config)
    assert "foo" in res

    # 2. Test group_by_package = True, line starts with "from"
    config = Config(group_by_package=True)
    res = section_key("from foo import bar, baz", config)
    assert "import" not in res

    # 3. Test lexicographical = True
    config = Config(lexicographical=True)
    res = section_key("import os", config)
    assert res.startswith("B")

    # 4. Test sort_relative_in_force_sorted_sections = True, reverse_relative = True / False
    config_rev = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=True)
    res_rev = section_key("from .foo import bar", config_rev)
    assert "." in res_rev

    config_no_rev = Config(sort_relative_in_force_sorted_sections=True, reverse_relative=False)
    res_no_rev = section_key("from .foo import bar", config_no_rev)
    assert "." in res_no_rev

    # 5. Test line.split(" ")[0] in config.force_to_top
    config = Config(force_to_top=["foo"])
    res = section_key("foo import bar", config)
    assert res.startswith("A")

    # 6. Test honor_case_in_force_sorted_sections = True, case_sensitive != order_by_type
    # With ' import ' (len > 1 split)
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=True,
        order_by_type=False,
    )
    res = section_key("Foo import Bar", config)
    assert "bar" in res  # names lowercased, module_name untouched

    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("Foo import Bar", config)
    assert "foo" in res  # module_name lowercased, names untouched

    # Without ' import ' (len == 1 split), case_sensitive = False
    config = Config(
        honor_case_in_force_sorted_sections=True,
        case_sensitive=False,
        order_by_type=True,
    )
    res = section_key("Foo", config)
    assert "foo" in res

    # 7. Test length_sort = True
    config = Config(length_sort=True)
    res = section_key("os", config)
    assert "2" in res
