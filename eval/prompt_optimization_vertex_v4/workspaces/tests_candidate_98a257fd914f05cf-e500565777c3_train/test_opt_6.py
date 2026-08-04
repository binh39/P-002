# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [631, 632], [631, 633]]}

from isort.output import _with_straight_imports
from isort.parse import ParsedContent
from isort.settings import Config


def _create_dummy_parsed_content():
    return ParsedContent(
        in_lines=[],
        lines_without_imports=[],
        import_index=0,
        place_imports={},
        import_placements={},
        as_map={"straight": {}},
        imports={"DEFAULT": {"straight": {}}},
        categorized_comments={"above": {"straight": {}}, "straight": {}},
        change_count=0,
        original_line_count=0,
        line_separator="\n",
        sections=[],
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
        section="DEFAULT",
        remove_imports=[],
        import_type="import",
    )
    assert res == []


def test_with_straight_imports_combine_with_comments():
    parsed = _create_dummy_parsed_content()
    parsed.categorized_comments["above"]["straight"]["mod1"] = ["# above mod1"]
    parsed.categorized_comments["straight"]["mod1"] = ["# inline mod1"]
    parsed.categorized_comments["straight"]["mod2"] = ["# inline mod2"]

    config = Config(combine_straight_imports=True)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["mod1", "mod2"],
        section="DEFAULT",
        remove_imports=[],
        import_type="import",
    )
    assert res == ["# above mod1", "import mod1, mod2  # # inline mod1 # inline mod2"]


def test_with_straight_imports_combine_without_inline_comments():
    parsed = _create_dummy_parsed_content()
    config = Config(combine_straight_imports=True)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["mod1", "mod2"],
        section="DEFAULT",
        remove_imports=[],
        import_type="import",
    )
    assert res == ["import mod1, mod2"]


def test_with_straight_imports_normal_path():
    parsed = _create_dummy_parsed_content()
    # remove_imports hit
    # as_map with base module present and as import present
    parsed.as_map["straight"]["mod1"] = ["alias1"]
    parsed.imports["DEFAULT"]["straight"]["mod1"] = True

    # without as_map
    # comments above
    parsed.categorized_comments["above"]["straight"]["mod2"] = ["# above mod2"]
    parsed.categorized_comments["straight"]["mod2"] = ["# inline mod2"]

    config = Config(combine_straight_imports=False)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["mod1", "remove_mod", "mod2"],
        section="DEFAULT",
        remove_imports=["remove_mod"],
        import_type="import",
    )

    assert any("import mod1" in line for line in res)
    assert any("import mod1 as alias1" in line for line in res)
    assert "# above mod2" in res
    assert any("import mod2" in line for line in res)
