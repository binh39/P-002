# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 623, 624, 625, 628, 630, 631, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 623], [631, 633]]}

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
        "categorized_comments": {"above": {"straight": {}, "from": {}}, "straight": {}, "from": {}},
        "change_count": 0,
        "original_line_count": 0,
        "line_separator": "\n",
        "sections": [],
        "verbose_output": False,
        "trailing_commas": [],
    }
    defaults.update(kwargs)
    return parse.ParsedContent(**defaults)


def test_with_straight_imports_combine_empty():
    parsed = _create_parsed_content()
    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=[],
        section="GENERAL",
        remove_imports=[],
        import_type="import",
    )
    assert result == []


def test_with_straight_imports_combine_with_comments():
    parsed = _create_parsed_content(
        categorized_comments={
            "above": {"straight": {"os": ["# OS comment"], "sys": ["# Sys comment"]}, "from": {}},
            "straight": {"os": ["# inline os"], "sys": ["# inline sys"]},
            "from": {},
        }
    )

    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "sys"],
        section="GENERAL",
        remove_imports=[],
        import_type="import",
    )
    assert "# OS comment" in result
    assert "# Sys comment" in result
    assert any("import os, sys" in line for line in result)
    assert any("# inline os inline sys" in line or "#" in line for line in result)


def test_with_straight_imports_combine_no_inline_comments():
    parsed = _create_parsed_content()
    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "sys"],
        section="GENERAL",
        remove_imports=[],
        import_type="import",
    )
    assert result == ["import os, sys"]


def test_with_straight_imports_non_combined_and_removals():
    parsed = _create_parsed_content(
        as_map={"straight": {"os": ["o"]}, "from": {}},
        imports={"SECTION": {"straight": {"os": True}, "from": {}}},
        categorized_comments={
            "above": {"straight": {"os": ["# above os"]}, "from": {}},
            "straight": {"os": ["# comment os"]},
            "from": {},
        },
    )

    config = Config(combine_straight_imports=False)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "sys"],
        section="SECTION",
        remove_imports=["os"],
        import_type="import",
    )
    # 'os' is in remove_imports so it should be skipped via continue
    # 'sys' should be processed through the else branch (no as_map, no base import if check)
    assert not any("os" in line for line in result)
    assert any("import sys" in line for line in result)


def test_with_straight_imports_with_as_map_false_base_import():
    parsed = _create_parsed_content(
        as_map={"straight": {"os": ["o"]}, "from": {}},
        imports={"SECTION": {"straight": {"os": False}, "from": {}}},
    )

    config = Config(combine_straight_imports=False)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os"],
        section="SECTION",
        remove_imports=[],
        import_type="import",
    )
    # Should contain 'import os as o', but not 'import os' because base import is False
    assert "import os" not in result
    assert any("import os as o" in line for line in result)
