# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [631, 632], [631, 633]]}

from collections.abc import Iterable
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
        as_map={"straight": {}, "from": {}},
        imports={"THIRDPARTY": {"straight": {}, "from": {}}},
        categorized_comments={"above": {"straight": {}, "from": {}}, "straight": {}, "from": {}},
        change_count=0,
        original_line_count=0,
        line_separator="\n",
        sections=[],
        verbose_output=False,
        trailing_commas=[],
    )


def test_with_straight_imports_combine_empty():
    parsed = create_empty_parsed_content()
    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=[],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert result == []


def test_with_straight_imports_combine_with_comments():
    parsed = create_empty_parsed_content()
    parsed.categorized_comments["above"]["straight"]["modA"] = ["# Above A"]
    parsed.categorized_comments["straight"]["modB"] = ["# Inline B"]
    
    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modA", "modB"],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert "# Above A" in result
    assert "import modA, modB  # # Inline B" in result


def test_with_straight_imports_combine_no_inline_comments():
    parsed = create_empty_parsed_content()
    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modA", "modB"],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert result == ["import modA, modB"]


def test_with_straight_imports_regular_flow():
    parsed = create_empty_parsed_content()
    parsed.as_map["straight"]["modA"] = ["aliasA"]
    parsed.imports["THIRDPARTY"]["straight"]["modA"] = True
    parsed.categorized_comments["above"]["straight"]["modA"] = ["# Above modA"]
    parsed.categorized_comments["straight"]["modA"] = ["# Inline A"]

    config = Config(combine_straight_imports=False)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modA", "remove_mod", "plain_mod"],
        section="THIRDPARTY",
        remove_imports=["remove_mod"],
        import_type="import",
    )
    
    assert "# Above modA" in result
    assert any("import modA" in line for line in result)
    assert any("import modA as aliasA" in line for line in result)
    assert any("import plain_mod" in line for line in result)
    assert not any("remove_mod" in line for line in result)
