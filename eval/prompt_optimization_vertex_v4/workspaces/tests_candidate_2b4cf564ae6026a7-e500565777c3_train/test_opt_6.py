# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47]]}

from isort.sorting import module_key
from isort.settings import Config


def test_module_key_comprehensive():
    # Test 1: match relative import with reverse_relative = True
    config1 = Config(reverse_relative=True)
    res1 = module_key(".foo", config1)
    assert res1.startswith("B")

    # Test 2: match relative import with reverse_relative = False (default)
    config2 = Config(reverse_relative=False)
    res2 = module_key(".foo", config2)
    assert res2.startswith("B")

    # Test 3: ignore_case = True
    config3 = Config()
    res3 = module_key("FOO", config3, ignore_case=True)
    assert "foo" in res3

    # Test 4: sub_imports and order_by_type branches
    # constant branch
    config4 = Config(order_by_type=True, constants=("const",))
    res4_const = module_key("const", config4, sub_imports=True)
    assert "A" in res4_const

    # classes branch
    config4 = Config(order_by_type=True, classes=("myclass",))
    res4_class = module_key("myclass", config4, sub_imports=True)
    assert "B" in res4_class

    # variables branch
    config4 = Config(order_by_type=True, variables=("var",))
    res4_var = module_key("var", config4, sub_imports=True)
    assert "C" in res4_var

    # isupper and len > 1 branch
    config4 = Config(order_by_type=True)
    res4_upper = module_key("ABC", config4, sub_imports=True)
    assert "A" in res4_upper

    # classes or starts with upper branch
    res4_start_upper = module_key("MyModule", config4, sub_imports=True)
    assert "B" in res4_start_upper

    # fallback else branch (prefix = C)
    res4_else = module_key("mymodule", config4, sub_imports=True)
    assert "C" in res4_else

    # Test 5: not config.case_sensitive
    config5 = Config(case_sensitive=False)
    res5 = module_key("FooBar", config5)
    assert "foobar" in res5

    # Test 6: length_sort conditions
    # config.length_sort = True
    config6_a = Config(length_sort=True)
    res6_a = module_key("test", config6_a)
    assert ":" in res6_a

    # config.length_sort_straight and straight_import = True
    config6_b = Config(length_sort_straight=True)
    res6_b = module_key("test", config6_b, straight_import=True)
    assert ":" in res6_b

    # section_name in length_sort_sections
    config6_c = Config(length_sort_sections=("my_section",))
    res6_c = module_key("test", config6_c, section_name="MY_SECTION")
    assert ":" in res6_c

    # Test 7: force_to_top branch ('A')
    config7 = Config(force_to_top=("topmodule",))
    res7 = module_key("topmodule", config7)
    assert res7.startswith("A")
