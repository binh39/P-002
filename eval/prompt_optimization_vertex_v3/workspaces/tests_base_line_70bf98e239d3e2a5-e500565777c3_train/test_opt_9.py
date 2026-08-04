# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}

from collections import defaultdict
from isort import parse
from isort.output import _with_straight_imports
from isort.settings import Config


def _create_parsed_content(**kwargs):
    defaults = {
        "in_lines": [],
        "lines_without_imports": [],
        "import_index": 0,
        "place_imports": {},
        "import_placements": {},
        "as_map": {"straight": defaultdict(list)},
        "imports": defaultdict(lambda: {"straight": defaultdict(bool)}),
        "categorized_comments": {
            "above": {"straight": defaultdict(list)},
            "straight": defaultdict(list),
        },
        "change_count": 0,
        "original_line_count": 0,
        "line_separator": "\n",
        "sections": [],
        "verbose_output": [],
        "trailing_commas": set(),
    }
    defaults.update(kwargs)
    return parse.ParsedContent(**defaults)


def test_with_straight_imports_combine_empty():
    config = Config(combine_straight_imports=True)
    parsed = _create_parsed_content()
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
    config = Config(combine_straight_imports=True)
    categorized_comments = {
        "above": {"straight": {"mod1": ["# Above mod1"]}},
        "straight": {"mod1": ["# inline mod1"]},
    }
    parsed = _create_parsed_content(categorized_comments=categorized_comments)

    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["mod1", "mod2"],
        section="DEFAULT",
        remove_imports=[],
        import_type="import",
    )
    assert result == ["# Above mod1", "import mod1, mod2  # # inline mod1"]


def test_with_straight_imports_combine_without_comments():
    config = Config(combine_straight_imports=True)
    parsed = _create_parsed_content()

    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["mod1", "mod2"],
        section="DEFAULT",
        remove_imports=[],
        import_type="import",
    )
    assert result == ["import mod1, mod2"]


def test_with_straight_imports_individual_and_as_imports():
    config = Config(combine_straight_imports=False)
    as_map = {"straight": {"mod_as": ["alias1"]}}
    imports = {"DEFAULT": {"straight": {"mod_as": True, "mod_plain": True}}}
    categorized_comments = {
        "above": {"straight": {"mod_plain": ["# Above plain"]}},
        "straight": {"mod_plain": ["# inline plain"]},
    }
    parsed = _create_parsed_content(
        as_map=as_map,
        imports=imports,
        categorized_comments=categorized_comments,
    )

    straight_modules = ["mod_remove", "mod_as", "mod_plain"]
    remove_imports = ["mod_remove"]

    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=straight_modules,
        section="DEFAULT",
        remove_imports=remove_imports,
        import_type="import",
    )

    assert "import mod_remove" not in " ".join(result)
    assert "import mod_as" in result
    assert "import mod_as as alias1" in result
    assert "# Above plain" in result
    assert any("import mod_plain" in line for line in result)
    assert "# inline plain" in " ".join(result)


def test_with_straight_imports_as_map_no_base_import():
    config = Config(combine_straight_imports=False)
    as_map = {"straight": {"mod_as": ["alias1"]}}
    imports = {"DEFAULT": {"straight": {"mod_as": False}}}
    parsed = _create_parsed_content(as_map=as_map, imports=imports)

    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["mod_as"],
        section="DEFAULT",
        remove_imports=[],
        import_type="import",
    )

    assert "import mod_as" not in result
    assert "import mod_as as alias1" in result
