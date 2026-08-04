# file: src\sample_repo\isort\isort\sorting.py:14-55
# asked: {"lines": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}
# gained: {"lines": [14, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 45, 46, 47, 49, 50, 51, 52, 54, 55], "branches": [[23, 24], [23, 27], [28, 29], [28, 31], [33, 34], [33, 46], [34, 35], [34, 36], [36, 37], [36, 38], [38, 39], [38, 40], [40, 41], [40, 42], [42, 43], [42, 45], [46, 47], [46, 49]]}

from isort.settings import Config
from isort.sorting import module_key


def test_module_key_comprehensive():
    # 1. Test relative module name with reverse_relative = True and False
    config_rev = Config(reverse_relative=True)
    res_rev = module_key(".foo", config_rev)
    assert ". foo" in res_rev

    config_norm = Config(reverse_relative=False)
    res_norm = module_key(".foo", config_norm)
    assert "._foo" in res_norm

    # 2. Test ignore_case = True vs False
    # By default, Config has case_sensitive = True (or case_sensitive determines lowercasing later).
    # But wait, case_sensitive defaults to True, so case_sensitive=False will lowercase everything.
    # To see the effect of ignore_case=True vs ignore_case=False, we can set case_sensitive=True
    # so that `module_name.lower()` in ignore_case=True makes a difference.
    config_ic = Config(case_sensitive=True)
    res_ic_true = module_key("FOO", config_ic, ignore_case=True)
    res_ic_false = module_key("FOO", config_ic, ignore_case=False)
    assert res_ic_true != res_ic_false

    # 3. Test sub_imports and order_by_type branches (constants, classes, variables, isupper>1, first letter upper, else)
    config_order = Config(
        order_by_type=True,
        constants=["CONST"],
        classes=["MyClass"],
        variables=["my_var"],
    )
    # constants -> prefix 'A'
    assert "A" in module_key("CONST", config_order, sub_imports=True)
    # classes -> prefix 'B'
    assert "B" in module_key("MyClass", config_order, sub_imports=True)
    # variables -> prefix 'C'
    assert "C" in module_key("my_var", config_order, sub_imports=True)
    # isupper and len > 1 -> prefix 'A'
    assert "A" in module_key("UPPER", config_order, sub_imports=True)
    # starts with upper -> prefix 'B'
    assert "B" in module_key("Other", config_order, sub_imports=True)
    # else -> prefix 'C'
    assert "C" in module_key("lower", config_order, sub_imports=True)

    # 4. Test case_sensitive = False
    config_cs = Config(case_sensitive=False)
    res_cs = module_key("FOO", config_cs)
    assert "foo" in res_cs

    # 5. Test length_sort combinations:
    # length_sort = True
    config_ls1 = Config(length_sort=True)
    assert ":" in module_key("foo", config_ls1)

    # length_sort_straight = True and straight_import = True
    config_ls2 = Config(length_sort_straight=True)
    assert ":" in module_key("foo", config_ls2, straight_import=True)

    # section_name in length_sort_sections
    config_ls3 = Config(length_sort_sections=["custom_section"])
    assert ":" in module_key("foo", config_ls3, section_name="CUSTOM_SECTION")

    # 6. Test force_to_top (membership in force_to_top yields 'A', otherwise 'B')
    config_ftt = Config(force_to_top=["top_mod"])
    res_top = module_key("top_mod", config_ftt)
    assert res_top.startswith("A")

    res_not_top = module_key("other_mod", config_ftt)
    assert res_not_top.startswith("B")
