# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}

from collections import defaultdict
from isort.output import _with_straight_imports
from isort.parse import ParsedContent
from isort.settings import Config


def _create_parsed_content(**kwargs):
    defaults = {
        "in_lines": [],
        "lines_without_imports": [],
        "import_index": 0,
        "place_imports": {},
        "import_placements": {},
        "as_map": {"straight": {}, "from": {}},
        "imports": defaultdict(lambda: {"straight": defaultdict(dict), "from": defaultdict(dict)}),
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
    return ParsedContent(**defaults)


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


def test_with_straight_imports_combine_with_comments_and_inline():
    parsed = _create_parsed_content()
    parsed.categorized_comments["above"]["straight"]["modA"] = ["# comment A"]
    parsed.categorized_comments["straight"]["modA"] = ["inline A"]
    parsed.categorized_comments["straight"]["modB"] = ["inline B"]

    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modA", "modB"],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert result == [
        "# comment A",
        "import modA, modB  # inline A inline B",
    ]


def test_with_straight_imports_combine_no_inline_comments():
    parsed = _create_parsed_content()
    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modA", "modB"],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert result == [
        "import modA, modB",
    ]


def test_with_straight_imports_normal_flow():
    imports_dict = defaultdict(lambda: {"straight": defaultdict(dict), "from": defaultdict(dict)})
    imports_dict["THIRDPARTY"]["straight"]["modA"] = True

    parsed = _create_parsed_content(
        as_map={"straight": {"modA": ["aliasA"]}, "from": {}},
        imports=imports_dict,
    )
    parsed.categorized_comments["above"]["straight"]["modA"] = ["# above modA"]
    parsed.categorized_comments["straight"]["modA"] = ["# inline modA"]
    parsed.categorized_comments["above"]["straight"]["modC"] = ["# above modC"]

    config = Config(combine_straight_imports=False)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modA", "modB", "modC"],
        section="THIRDPARTY",
        remove_imports=["modB"],  # should be skipped
        import_type="import",
    )
    assert len(result) > 0
    assert "import modB" not in " ".join(result)


def test_with_straight_imports_as_import_empty_base():
    imports_dict = defaultdict(lambda: {"straight": defaultdict(dict), "from": defaultdict(dict)})
    imports_dict["THIRDPARTY"]["straight"]["modA"] = False

    parsed = _create_parsed_content(
        as_map={"straight": {"modA": ["aliasA"]}, "from": {}},
        imports=imports_dict,
    )

    config = Config(combine_straight_imports=False)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modA"],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert result == ["import modA as aliasA"]
