# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [621, 622], [621, 623], [631, 632], [631, 633]]}

from isort.parse import ParsedContent
from isort.output import _with_straight_imports
from isort.settings import Config


def _create_dummy_parsed(
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
    parsed = _create_dummy_parsed()
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
    categorized_comments = {
        "above": {"straight": {"os": ["# os comment above"]}, "from": {}},
        "straight": {"sys": ["sys comment"]},
        "from": {},
    }
    parsed = _create_dummy_parsed(categorized_comments=categorized_comments)

    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "sys"],
        section="DEFAULT",
        remove_imports=[],
        import_type="import",
    )
    assert result == [
        "# os comment above",
        "import os, sys  # sys comment",
    ]


def test_with_straight_imports_combine_without_comments():
    parsed = _create_dummy_parsed()
    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "sys"],
        section="DEFAULT",
        remove_imports=[],
        import_type="import",
    )
    assert result == ["import os, sys"]


def test_with_straight_imports_standard_and_as_imports():
    as_map = {
        "straight": {
            "os": ["os_alias"],
            "sys": ["sys_alias"],
        },
        "from": {},
    }
    imports = {
        "DEFAULT": {
            "straight": {
                "os": True,
                "sys": False,
            }
        }
    }
    categorized_comments = {
        "above": {"straight": {"os": ["# above os"]}, "from": {}},
        "straight": {"os": ["inline os"]},
        "from": {},
    }
    parsed = _create_dummy_parsed(
        as_map=as_map,
        imports=imports,
        categorized_comments=categorized_comments,
    )

    config = Config(combine_straight_imports=False)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "sys", "removed_mod"],
        section="DEFAULT",
        remove_imports=["removed_mod"],
        import_type="import",
    )
    assert "# above os" in result
    assert any("import os" in line for line in result)
    assert "import os as os_alias" in result
    assert "import sys as sys_alias" in result
    assert not any("sys" in line and "import sys" == line.strip() for line in result)
