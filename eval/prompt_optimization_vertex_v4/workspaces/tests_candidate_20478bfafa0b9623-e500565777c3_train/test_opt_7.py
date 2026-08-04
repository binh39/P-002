# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}

from collections import defaultdict
from isort import parse
from isort.settings import Config
from isort.output import _with_straight_imports


def create_empty_parsed_content():
    return parse.ParsedContent(
        in_lines=[],
        lines_without_imports=[],
        import_index=0,
        place_imports={},
        import_placements={},
        as_map={"straight": defaultdict(list)},
        imports=defaultdict(lambda: {"straight": defaultdict(bool)}),
        categorized_comments={
            "above": {"straight": defaultdict(list)},
            "straight": defaultdict(list),
        },
        change_count=0,
        original_line_count=0,
        line_separator="\n",
        sections=[],
        verbose_output=[],
        trailing_commas=set(),
    )


def test_with_straight_imports_combine_empty():
    parsed = create_empty_parsed_content()
    config = Config(combine_straight_imports=True)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=[],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert res == []


def test_with_straight_imports_combine_with_comments():
    parsed = create_empty_parsed_content()
    parsed.categorized_comments["above"]["straight"]["mod1"] = ["# above mod1"]
    parsed.categorized_comments["straight"]["mod1"] = ["# inline mod1"]
    parsed.categorized_comments["straight"]["mod2"] = ["# inline mod2"]

    config = Config(combine_straight_imports=True)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["mod1", "mod2"],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert res == [
        "# above mod1",
        "import mod1, mod2  # # inline mod1 # inline mod2",
    ]


def test_with_straight_imports_combine_without_comments():
    parsed = create_empty_parsed_content()
    config = Config(combine_straight_imports=True)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["mod1", "mod2"],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert res == ["import mod1, mod2"]


def test_with_straight_imports_normal_flow():
    parsed = create_empty_parsed_content()
    parsed.as_map["straight"]["mod_as"] = ["alias1"]
    parsed.imports["THIRDPARTY"]["straight"]["mod_as"] = True

    parsed.categorized_comments["above"]["straight"]["mod_reg"] = ["# comment above reg"]
    parsed.categorized_comments["straight"]["mod_reg"] = ["# inline reg"]

    config = Config(combine_straight_imports=False)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["mod_remove", "mod_as", "mod_reg"],
        section="THIRDPARTY",
        remove_imports=["mod_remove"],
        import_type="import",
    )

    assert any("mod_remove" not in line for line in res)
    assert "import mod_as" in res[0]
    assert "import mod_as as alias1" in res[1]
    assert "# comment above reg" in res
    assert any("import mod_reg  # # inline reg" in line for line in res)


def test_with_straight_imports_as_map_no_base_import():
    parsed = create_empty_parsed_content()
    parsed.as_map["straight"]["mod_as"] = ["alias1"]
    parsed.imports["THIRDPARTY"]["straight"]["mod_as"] = False

    config = Config(combine_straight_imports=False)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["mod_as"],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert res == ["import mod_as as alias1"]
