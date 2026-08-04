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
    return ParsedContent(
        in_lines=[],
        lines_without_imports=[],
        import_index=0,
        place_imports={},
        import_placements={},
        as_map=as_map or {"straight": {}, "from": {}},
        imports=imports or {},
        categorized_comments=categorized_comments
        or {
            "above": {"straight": {}, "from": {}},
            "straight": {},
            "from": {},
        },
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
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert result == []


def test_with_straight_imports_combine_with_comments():
    parsed = _create_parsed_content(
        categorized_comments={
            "above": {"straight": {"os": ["# OS comment"]}, "from": {}},
            "straight": {"sys": ["# inline sys"]},
            "from": {},
        }
    )

    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "sys"],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert result == ["# OS comment", "import os, sys  # # inline sys"]


def test_with_straight_imports_combine_without_inline_comments():
    parsed = _create_parsed_content()
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


def test_with_straight_imports_normal_flow_and_branches():
    parsed = _create_parsed_content(
        as_map={
            "straight": {
                "mod_as": ["alias1"],
                "mod_as_no_base": ["alias2"],
            },
            "from": {},
        },
        imports={
            "THIRDPARTY": {
                "straight": {
                    "mod_as": True,
                    "mod_as_no_base": False,
                }
            }
        },
        categorized_comments={
            "above": {
                "straight": {
                    "mod_normal": ["# above normal"],
                },
                "from": {},
            },
            "straight": {
                "mod_normal": ["# inline normal"],
            },
            "from": {},
        },
    )

    config = Config(combine_straight_imports=False)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=[
            "mod_removed",
            "mod_normal",
            "mod_as",
            "mod_as_no_base",
        ],
        section="THIRDPARTY",
        remove_imports=["mod_removed"],
        import_type="import",
    )

    assert any("mod_removed" in line for line in result) is False
    assert "# above normal" in result
    assert any("import mod_normal" in line for line in result)
    assert any("import mod_as as alias1" in line for line in result)
    assert any("import mod_as" in line for line in result)
    assert any("import mod_as_no_base as alias2" in line for line in result)
    # Check that base import for mod_as_no_base is not present because its flag was False
    assert "import mod_as_no_base" not in [r.strip() for r in result]
