# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [621, 622], [621, 623], [631, 632], [631, 633]]}

from isort import parse
from isort.output import _with_straight_imports
from isort.settings import Config


def _create_dummy_parsed() -> parse.ParsedContent:
    return parse.ParsedContent(
        in_lines=[],
        lines_without_imports=[],
        import_index=0,
        place_imports={},
        import_placements={},
        as_map={"straight": {}, "from": {}},
        imports={"STDLIB": {"straight": {}, "from": {}}},
        categorized_comments={"above": {"straight": {}, "from": {}}, "straight": {}, "from": {}},
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
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=[],
        section="STDLIB",
        remove_imports=[],
        import_type="import",
    )
    assert res == []


def test_with_straight_imports_combine_with_comments_and_inline():
    parsed = _create_dummy_parsed()
    parsed.categorized_comments["above"]["straight"]["os"] = ["# comment os"]
    parsed.categorized_comments["straight"]["sys"] = ["# comment sys"]
    config = Config(combine_straight_imports=True)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "sys"],
        section="STDLIB",
        remove_imports=[],
        import_type="import",
    )
    assert "# comment os" in res
    assert any("import os, sys" in line for line in res)
    assert any("comment sys" in line for line in res)


def test_with_straight_imports_combine_no_inline_comments():
    parsed = _create_dummy_parsed()
    config = Config(combine_straight_imports=True)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "sys"],
        section="STDLIB",
        remove_imports=[],
        import_type="import",
    )
    assert res == ["import os, sys"]


def test_with_straight_imports_individual_removal_and_as_map():
    parsed = _create_dummy_parsed()
    parsed.as_map["straight"]["os"] = ["os_alias"]
    parsed.imports["STDLIB"]["straight"]["os"] = True
    parsed.categorized_comments["above"]["straight"]["os"] = ["# above os"]
    parsed.categorized_comments["straight"]["os"] = ["# inline os"]

    config = Config(combine_straight_imports=False)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "removed_mod"],
        section="STDLIB",
        remove_imports=["removed_mod"],
        import_type="import",
    )
    assert "# above os" in res
    assert any("import os" in line for line in res)
    assert any("import os as os_alias" in line for line in res)


def test_with_straight_imports_as_map_empty_base_import():
    parsed = _create_dummy_parsed()
    parsed.as_map["straight"]["os"] = ["os_alias"]
    parsed.imports["STDLIB"]["straight"]["os"] = False

    config = Config(combine_straight_imports=False)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os"],
        section="STDLIB",
        remove_imports=[],
        import_type="import",
    )
    assert res == ["import os as os_alias"]
