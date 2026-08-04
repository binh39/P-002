# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}

from collections.abc import Iterable
from isort import parse
from isort.settings import Config
from isort.output import _with_straight_imports


def create_mock_parsed_content():
    return parse.ParsedContent(
        in_lines=[],
        lines_without_imports=[],
        import_index=0,
        place_imports={},
        import_placements={},
        as_map={"straight": {}},
        imports={"THIRDPARTY": {"straight": {}}},
        categorized_comments={"above": {"straight": {}}, "straight": {}},
        change_count=0,
        original_line_count=0,
        line_separator="\n",
        sections=None,
        verbose_output=[],
        trailing_commas=set(),
    )


def test_with_straight_imports_combine_empty():
    parsed = create_mock_parsed_content()
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
    parsed = create_mock_parsed_content()
    parsed.categorized_comments["above"]["straight"]["os"] = ["# OS comment"]
    parsed.categorized_comments["straight"]["os"] = ["inline os"]
    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "sys"],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert result == ["# OS comment", "import os, sys  # inline os"]


def test_with_straight_imports_combine_without_comments():
    parsed = create_mock_parsed_content()
    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "sys"],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert result == ["import os, sys"]


def test_with_straight_imports_individual_with_remove_and_as():
    parsed = create_mock_parsed_content()
    parsed.as_map["straight"]["os"] = ["alias_os"]
    parsed.imports["THIRDPARTY"]["straight"]["os"] = True
    parsed.categorized_comments["above"]["straight"]["sys"] = ["# sys above"]
    parsed.categorized_comments["straight"]["sys"] = ["sys inline"]

    config = Config(combine_straight_imports=False)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "remove_mod", "sys"],
        section="THIRDPARTY",
        remove_imports=["remove_mod"],
        import_type="import",
    )
    assert result == [
        "import os",
        "import os as alias_os",
        "# sys above",
        "import sys  # sys inline",
    ]


def test_with_straight_imports_as_map_no_base():
    parsed = create_mock_parsed_content()
    parsed.as_map["straight"]["os"] = ["alias_os"]
    parsed.imports["THIRDPARTY"]["straight"]["os"] = False

    config = Config(combine_straight_imports=False)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os"],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert result == ["import os as alias_os"]
