# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [631, 632], [631, 633]]}

import pytest
from isort import parse
from isort.settings import Config
from isort.output import _with_straight_imports


def create_dummy_parsed():
    return parse.ParsedContent(
        in_lines=[],
        lines_without_imports=[],
        import_index=0,
        place_imports={},
        import_placements={},
        as_map={"straight": {}},
        imports={"DEFAULT": {"straight": {}}},
        categorized_comments={"above": {"straight": {}}, "straight": {}, "below": {"straight": {}}},
        change_count=0,
        original_line_count=0,
        line_separator="\n",
        sections=[],
        verbose_output=[],
        trailing_commas=set(),
    )


def test_with_straight_imports_combine_empty():
    parsed = create_dummy_parsed()
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


def test_with_straight_imports_combine_with_comments_and_inline():
    parsed = create_dummy_parsed()
    parsed.categorized_comments["above"]["straight"]["mod1"] = ["# Above mod1"]
    parsed.categorized_comments["straight"]["mod2"] = ["# Inline mod2"]
    
    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["mod1", "mod2"],
        section="DEFAULT",
        remove_imports=[],
        import_type="import",
    )
    assert result == [
        "# Above mod1",
        "import mod1, mod2  # # Inline mod2",
    ]


def test_with_straight_imports_combine_without_inline():
    parsed = create_dummy_parsed()
    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["mod1", "mod2"],
        section="DEFAULT",
        remove_imports=[],
        import_type="import",
    )
    assert result == [
        "import mod1, mod2",
    ]


def test_with_straight_imports_uncombined_removed_and_as_imports():
    parsed = create_dummy_parsed()
    parsed.as_map["straight"]["mod_as"] = ["alias"]
    parsed.imports["DEFAULT"]["straight"]["mod_as"] = True
    
    parsed.categorized_comments["above"]["straight"]["mod_regular"] = ["# Above regular"]
    parsed.categorized_comments["straight"]["mod_regular"] = ["# Inline regular"]

    config = Config(combine_straight_imports=False)
    
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["mod_removed", "mod_as", "mod_regular"],
        section="DEFAULT",
        remove_imports=["mod_removed"],
        import_type="import",
    )
    
    assert any("mod_removed" not in line for line in result)
    assert any("import mod_as" in line for line in result)
    assert any("import mod_as as alias" in line for line in result)
