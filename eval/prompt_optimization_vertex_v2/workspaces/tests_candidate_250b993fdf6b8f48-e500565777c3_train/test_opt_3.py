# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 604, 606, 607, 608, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 630, 631, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [606, 607], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [621, 622], [631, 633]]}

from isort import parse
from isort.output import _with_straight_imports
from isort.settings import Config


def test_with_straight_imports_combined_with_inline_comments():
    parsed = parse.ParsedContent(
        in_lines=[],
        lines_without_imports=[],
        import_index=0,
        place_imports={},
        import_placements={},
        as_map={"straight": {}},
        imports={},
        categorized_comments={
            "above": {"straight": {"os": ["# OS comment"]}},
            "straight": {"sys": ["# sys comment"]},
        },
        change_count=0,
        original_line_count=0,
        line_separator="\n",
        sections=None,
        verbose_output=[],
        trailing_commas=set(),
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
    assert "import os, sys  # # sys comment" in result or "import os, sys" in result


def test_with_straight_imports_combined_empty_modules():
    parsed = parse.ParsedContent(
        in_lines=[],
        lines_without_imports=[],
        import_index=0,
        place_imports={},
        import_placements={},
        as_map={"straight": {}},
        imports={},
        categorized_comments={"above": {"straight": {}}, "straight": {}},
        change_count=0,
        original_line_count=0,
        line_separator="\n",
        sections=None,
        verbose_output=[],
        trailing_commas=set(),
    )
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


def test_with_straight_imports_individual_with_removal_and_as_map():
    parsed = parse.ParsedContent(
        in_lines=[],
        lines_without_imports=[],
        import_index=0,
        place_imports={},
        import_placements={},
        as_map={"straight": {"sys": ["s"]}},
        imports={
            "GENERAL": {
                "straight": {
                    "sys": True,
                    "os": True,
                }
            }
        },
        categorized_comments={
            "above": {"straight": {"os": ["# above os"]}},
            "straight": {"os": ["# inline os"]},
        },
        change_count=0,
        original_line_count=0,
        line_separator="\n",
        sections=None,
        verbose_output=[],
        trailing_commas=set(),
    )
    config = Config(combine_straight_imports=False)
    # Remove 'os', keep 'sys' (which has 'as' mapping and parsed.imports entry)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "sys"],
        section="GENERAL",
        remove_imports=["os"],
        import_type="import",
    )
    assert "# above os" not in result
    assert "import sys" in result
    assert "import sys as s" in result
