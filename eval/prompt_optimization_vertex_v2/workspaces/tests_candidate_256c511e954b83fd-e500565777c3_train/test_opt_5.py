# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}

from collections import defaultdict
from isort.output import _with_straight_imports
from isort.parse import ParsedContent
from isort.settings import Config


def _create_mock_parsed_content(**kwargs):
    defaults = {
        "in_lines": [],
        "lines_without_imports": [],
        "import_index": 0,
        "place_imports": {},
        "import_placements": {},
        "as_map": {"straight": defaultdict(list)},
        "imports": defaultdict(lambda: {"straight": defaultdict(lambda: True)}),
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
    parsed = _create_mock_parsed_content()
    config = Config(combine_straight_imports=True)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=[],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert res == []


def test_with_straight_imports_combine_with_comments_and_inline():
    categorized_comments = {
        "above": {"straight": {"os": ["# OS comment"]}},
        "straight": {"os": ["# inline os"], "sys": ["# inline sys"]},
    }
    parsed = _create_mock_parsed_content(categorized_comments=categorized_comments)

    config = Config(combine_straight_imports=True)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "sys"],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert res == ["# OS comment", "import os, sys  # # inline os # inline sys"]


def test_with_straight_imports_combine_no_inline_comments():
    parsed = _create_mock_parsed_content()
    config = Config(combine_straight_imports=True)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "sys"],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert res == ["import os, sys"]


def test_with_straight_imports_non_combine_remove_and_as_imports():
    as_map = {
        "straight": {
            "os": ["os_alias"],
            "json": ["json_alias"],
        }
    }
    imports = {
        "THIRDPARTY": {
            "straight": {
                "os": True,
                "json": False,
            }
        }
    }
    categorized_comments = {
        "above": {"straight": {"os": ["# above os"]}},
        "straight": {"os": ["# comment os"]},
    }
    parsed = _create_mock_parsed_content(
        as_map=as_map,
        imports=imports,
        categorized_comments=categorized_comments,
    )

    config = Config(combine_straight_imports=False)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "json", "sys", "removed_mod"],
        section="THIRDPARTY",
        remove_imports=["removed_mod"],
        import_type="import",
    )

    assert any("import os" in line for line in res)
    assert any("import os as os_alias" in line for line in res)
    assert any("import json as json_alias" in line for line in res)
    assert any("import sys" in line for line in res)
    assert not any("removed_mod" in line for line in res)
    assert "# above os" in res
