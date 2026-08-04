# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}

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
        "imports": {},
        "categorized_comments": {
            "above": {"straight": {}, "from": {}},
            "straight": {},
            "from": {},
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
    parsed = _create_parsed_content(
        categorized_comments={
            "above": {"straight": {"mod1": ["# Above mod1"]}, "from": {}},
            "straight": {"mod1": ["# Inline mod1"], "mod2": ["# Inline mod2"]},
            "from": {},
        }
    )

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
        "import mod1, mod2  # # Inline mod1 # Inline mod2",
    ]


def test_with_straight_imports_combine_without_inline_comments():
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


def test_with_straight_imports_remove_and_as_imports():
    config = Config(combine_straight_imports=False)
    parsed = _create_parsed_content(
        as_map={"straight": {"mod_as1": ["alias1"], "mod_as2": ["alias2"]}, "from": {}},
        imports={"DEFAULT": {"straight": {"mod_as1": True, "mod_as2": False}}},
        categorized_comments={
            "above": {"straight": {"mod_normal": ["# Above normal"]}, "from": {}},
            "straight": {"mod_normal": ["# Inline normal"]},
            "from": {},
        },
    )

    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["mod_remove", "mod_as1", "mod_as2", "mod_normal"],
        section="DEFAULT",
        remove_imports=["mod_remove"],
        import_type="import",
    )

    assert "import mod_remove" not in "".join(result)
    assert "import mod_as1" in result
    assert "import mod_as1 as alias1" in result
    # mod_as2 parent import is False, so only 'as' import should be added
    assert "import mod_as2" not in result
    assert "import mod_as2 as alias2" in result
    assert "# Above normal" in result
    assert any("import mod_normal" in line for line in result)
