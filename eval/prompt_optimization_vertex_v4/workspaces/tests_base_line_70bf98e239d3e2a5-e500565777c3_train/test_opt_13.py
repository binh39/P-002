# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}

from isort import parse
from isort.output import _with_straight_imports
from isort.settings import Config


def _make_parsed():
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
    parsed = _make_parsed()
    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=[],
        section="DEFAULT",
        remove_imports=[],
        import_type="import",
    )
    assert result == []


def test_with_straight_imports_combine_with_comments():
    parsed = _make_parsed()
    parsed.categorized_comments["above"]["straight"]["modA"] = ["# above modA"]
    parsed.categorized_comments["straight"]["modA"] = ["# inline modA"]
    parsed.categorized_comments["above"]["straight"]["modB"] = ["# above modB"]
    parsed.categorized_comments["straight"]["modB"] = ["# inline modB"]

    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modA", "modB"],
        section="DEFAULT",
        remove_imports=[],
        import_type="import",
    )
    assert "# above modA" in result
    assert "# above modB" in result
    assert "import modA, modB  # # inline modA # inline modB" in result


def test_with_straight_imports_combine_without_inline_comments():
    parsed = _make_parsed()
    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modA", "modB"],
        section="DEFAULT",
        remove_imports=[],
        import_type="import",
    )
    assert result == ["import modA, modB"]


def test_with_straight_imports_individual_and_as_imports():
    parsed = _make_parsed()
    parsed.as_map["straight"]["modA"] = ["aliasA"]
    parsed.imports["DEFAULT"] = {"straight": {"modA": True, "modB": True}}

    parsed.categorized_comments["above"]["straight"]["modA"] = ["# above modA"]
    parsed.categorized_comments["straight"]["modA"] = ["# inline"]

    config = Config(combine_straight_imports=False)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modA", "modB", "modRemove"],
        section="DEFAULT",
        remove_imports=["modRemove"],
        import_type="import",
    )

    assert "# above modA" in result
    assert any(line.startswith("import modA") for line in result)
    assert "import modA as aliasA" in result
    assert "import modB" in result
    assert not any("modRemove" in line for line in result)


def test_with_straight_imports_no_base_import_when_false():
    parsed = _make_parsed()
    parsed.as_map["straight"]["modA"] = ["aliasA"]
    parsed.imports["DEFAULT"] = {"straight": {"modA": False}}

    config = Config(combine_straight_imports=False)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modA"],
        section="DEFAULT",
        remove_imports=[],
        import_type="import",
    )

    assert "import modA" not in result
    assert "import modA as aliasA" in result
