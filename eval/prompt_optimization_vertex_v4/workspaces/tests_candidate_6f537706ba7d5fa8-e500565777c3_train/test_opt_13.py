# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}

from isort.output import _with_straight_imports
from isort.parse import ParsedContent
from isort.settings import Config


def _create_parsed_content(
    as_map=None,
    imports=None,
    categorized_comments=None,
):
    if as_map is None:
        as_map = {"straight": {}, "from": {}}
    if imports is None:
        imports = {}
    if categorized_comments is None:
        categorized_comments = {
            "above": {"straight": {}, "from": {}},
            "straight": {},
            "from": {},
        }

    return ParsedContent(
        in_lines=[],
        lines_without_imports=[],
        import_index=0,
        place_imports={},
        import_placements={},
        as_map=as_map,
        imports=imports,
        categorized_comments=categorized_comments,
        change_count=0,
        original_line_count=0,
        line_separator="\n",
        sections=[],
        verbose_output=[],
        trailing_commas=set(),
    )


def test_with_straight_imports_combine_empty():
    parsed = _create_parsed_content()
    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=[],
        section="STDLIB",
        remove_imports=[],
        import_type="import",
    )
    assert result == []


def test_with_straight_imports_combine_with_comments_and_inline():
    categorized_comments = {
        "above": {"straight": {"modA": ["# Above A"]}, "from": {}},
        "straight": {"modA": ["inline A"], "modB": ["inline B"]},
        "from": {},
    }
    parsed = _create_parsed_content(categorized_comments=categorized_comments)

    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modA", "modB"],
        section="STDLIB",
        remove_imports=[],
        import_type="import",
    )
    assert result == [
        "# Above A",
        "import modA, modB  # inline A inline B",
    ]


def test_with_straight_imports_combine_without_inline_comments():
    parsed = _create_parsed_content()
    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modA", "modB"],
        section="STDLIB",
        remove_imports=[],
        import_type="import",
    )
    assert result == ["import modA, modB"]


def test_with_straight_imports_uncombined_removed_and_as_imports():
    as_map = {"straight": {"modA": ["aliasA"], "modB": ["aliasB"]}, "from": {}}
    imports = {
        "STDLIB": {
            "straight": {
                "modA": True,
                "modB": False,
            }
        }
    }
    categorized_comments = {
        "above": {"straight": {"modA": ["# Above A"]}, "from": {}},
        "straight": {"modA": ["inline A"]},
        "from": {},
    }
    parsed = _create_parsed_content(
        as_map=as_map, imports=imports, categorized_comments=categorized_comments
    )

    config = Config(combine_straight_imports=False)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modRemoved", "modA", "modB", "modPlain"],
        section="STDLIB",
        remove_imports=["modRemoved"],
        import_type="import",
    )
    assert result == [
        "# Above A",
        "import modA  # inline A",
        "import modA as aliasA",
        "import modB as aliasB",
        "import modPlain",
    ]
