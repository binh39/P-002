# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [631, 632], [631, 633]]}

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
        "as_map": {"straight": {}, "from": {}},
        "imports": {"GENERAL": {"straight": {}, "from": {}}},
        "categorized_comments": {
            "above": {"straight": {}, "from": {}},
            "straight": {},
            "from": {},
            "global": [],
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
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=[],
        section="GENERAL",
        remove_imports=[],
        import_type="import",
    )
    assert res == []


def test_with_straight_imports_combine_with_comments():
    config = Config(combine_straight_imports=True)
    categorized_comments = {
        "above": {"straight": {"mod1": ["# above mod1"]}, "from": {}},
        "straight": {"mod2": ["# inline mod2"]},
        "from": {},
        "global": [],
    }
    parsed = _create_parsed_content(categorized_comments=categorized_comments)

    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["mod1", "mod2"],
        section="GENERAL",
        remove_imports=[],
        import_type="import",
    )
    assert res == [
        "# above mod1",
        "import mod1, mod2  # # inline mod2",
    ]


def test_with_straight_imports_combine_no_inline_comments():
    config = Config(combine_straight_imports=True)
    parsed = _create_parsed_content()
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["mod1", "mod2"],
        section="GENERAL",
        remove_imports=[],
        import_type="import",
    )
    assert res == ["import mod1, mod2"]


def test_with_straight_imports_individual_with_removal_and_as_map():
    config = Config(combine_straight_imports=False)
    as_map = {"straight": {"mod_as": ["alias1"]}, "from": {}}
    imports = {"GENERAL": {"straight": {"mod_as": True, "mod_plain": True}, "from": {}}}
    categorized_comments = {
        "above": {
            "straight": {
                "mod_remove": ["# comment removal"],
                "mod_as": ["# comment above as"],
            },
            "from": {},
        },
        "straight": {"mod_as": ["# inline as"]},
        "from": {},
        "global": [],
    }
    parsed = _create_parsed_content(
        as_map=as_map, imports=imports, categorized_comments=categorized_comments
    )

    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["mod_remove", "mod_as", "mod_plain"],
        section="GENERAL",
        remove_imports=["mod_remove"],
        import_type="import",
    )
    assert len(res) > 0
    assert any("mod_as as alias1" in line for line in res)
    assert any("mod_plain" in line for line in res)
    assert not any("mod_remove" in line for line in res)
