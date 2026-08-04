# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [631, 632]]}

from collections.abc import Iterable
from isort import parse
from isort.settings import Config
from isort.output import _with_straight_imports


def _create_dummy_parsed_content():
    return parse.ParsedContent(
        in_lines=[],
        lines_without_imports=[],
        import_index=0,
        place_imports={},
        import_placements={},
        as_map={"straight": {}},
        imports={},
        categorized_comments={"above": {"straight": {}}, "straight": {}},
        change_count=0,
        original_line_count=0,
        line_separator="\n",
        sections=None,
        verbose_output=[],
        trailing_commas=set(),
    )


def test_with_straight_imports_combine_empty():
    parsed = _create_dummy_parsed_content()
    config = Config(combine_straight_imports=True)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=[],
        section="STDLIB",
        remove_imports=[],
        import_type="import",
    )
    assert res == []


def test_with_straight_imports_combine_with_comments():
    parsed = _create_dummy_parsed_content()
    parsed.categorized_comments["above"]["straight"]["modA"] = ["# above modA"]
    parsed.categorized_comments["straight"]["modA"] = ["# inline modA"]
    config = Config(combine_straight_imports=True)

    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modA", "modB"],
        section="STDLIB",
        remove_imports=[],
        import_type="import",
    )
    assert len(res) == 2
    assert res[0] == "# above modA"
    assert "import modA, modB" in res[1]


def test_with_straight_imports_combine_without_inline_comments():
    parsed = _create_dummy_parsed_content()
    config = Config(combine_straight_imports=True)

    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modA", "modB"],
        section="STDLIB",
        remove_imports=[],
        import_type="import",
    )
    assert res == ["import modA, modB"]


def test_with_straight_imports_normal_flow():
    parsed = _create_dummy_parsed_content()
    remove_imports = ["mod_removed"]
    
    parsed.as_map["straight"]["mod1"] = ["alias1"]
    parsed.imports["STDLIB"] = {"straight": {"mod1": True}}
    parsed.categorized_comments["above"]["straight"]["mod1"] = ["# comment above mod1"]
    parsed.categorized_comments["straight"]["mod1"] = ["# comment inline mod1"]

    parsed.categorized_comments["above"]["straight"]["mod2"] = ["# comment above mod2"]

    config = Config(combine_straight_imports=False)

    straight_modules = ["mod_removed", "mod1", "mod2"]
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=straight_modules,
        section="STDLIB",
        remove_imports=remove_imports,
        import_type="import",
    )
    
    assert any("mod1" in line for line in res)
    assert any("mod2" in line for line in res)
    assert not any("mod_removed" in line for line in res)
