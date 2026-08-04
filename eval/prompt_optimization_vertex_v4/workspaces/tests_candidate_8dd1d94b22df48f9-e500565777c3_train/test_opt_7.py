# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}

from collections import defaultdict
from isort.parse import ParsedContent
from isort.output import _with_straight_imports
from isort.settings import Config


def _make_parsed_content(**kwargs):
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
    return ParsedContent(**defaults)


def test_with_straight_imports_combine_empty():
    config = Config(combine_straight_imports=True)
    parsed = _make_parsed_content()
    res = _with_straight_imports(parsed, config, [], "DEFAULT", [], "import")
    assert res == []


def test_with_straight_imports_combine_with_comments():
    config = Config(combine_straight_imports=True)
    parsed = _make_parsed_content()
    parsed.categorized_comments["above"]["straight"]["os"] = ["# above os"]
    parsed.categorized_comments["straight"]["os"] = ["# inline os"]

    res = _with_straight_imports(
        parsed, config, ["os", "sys"], "DEFAULT", [], "import"
    )
    assert res == ["# above os", "import os, sys  # # inline os"]


def test_with_straight_imports_combine_no_inline_comments():
    config = Config(combine_straight_imports=True)
    parsed = _make_parsed_content()

    res = _with_straight_imports(
        parsed, config, ["os", "sys"], "DEFAULT", [], "import"
    )
    assert res == ["import os, sys"]


def test_with_straight_imports_normal_flow_and_removals():
    config = Config(combine_straight_imports=False)
    
    as_map = {"straight": {"os": ["os_alias"]}}
    imports = {"DEFAULT": {"straight": {"os": True, "sys": True}}}
    categorized_comments = {
        "above": {
            "straight": {
                "os": ["# above os"],
                "sys": ["# above sys"],
            }
        },
        "straight": {
            "os": ["# inline os"]
        }
    }
    parsed = _make_parsed_content(
        as_map=as_map,
        imports=imports,
        categorized_comments=categorized_comments,
    )

    straight_modules = ["os", "sys", "removed_mod"]
    remove_imports = ["removed_mod"]

    res = _with_straight_imports(
        parsed, config, straight_modules, "DEFAULT", remove_imports, "import"
    )
    assert any("import os" in line for line in res)
    assert any("import os as os_alias" in line for line in res)
    assert any("import sys" in line for line in res)
    assert "# above os" in res
    assert "# above sys" in res


def test_with_straight_imports_as_map_empty_base():
    config = Config(combine_straight_imports=False)
    
    as_map = {"straight": {"os": ["os_alias"]}}
    imports = {"DEFAULT": {"straight": {"os": False}}}
    parsed = _make_parsed_content(
        as_map=as_map,
        imports=imports,
    )

    res = _with_straight_imports(
        parsed, config, ["os"], "DEFAULT", [], "import"
    )
    assert res == ["import os as os_alias"]
