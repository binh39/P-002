# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [631, 632], [631, 633]]}

from isort.output import _with_straight_imports
from isort.parse import ParsedContent
from isort.settings import Config

def make_parsed():
    return ParsedContent(
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
        sections=[],
        verbose_output=[],
        trailing_commas=set(),
    )

def test_with_straight_imports_combine_empty():
    parsed = make_parsed()
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
    parsed = make_parsed()
    parsed.categorized_comments["above"]["straight"]["modA"] = ["# comment A"]
    parsed.categorized_comments["straight"]["modA"] = ["# inline A"]
    config = Config(combine_straight_imports=True)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modA", "modB"],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert "# comment A" in res
    assert any("import modA, modB" in line for line in res)
    assert any("# inline A" in line for line in res)

def test_with_straight_imports_combine_no_inline_comments():
    parsed = make_parsed()
    config = Config(combine_straight_imports=True)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modA", "modB"],
        section="THIRDPARTY",
        remove_imports=[],
        import_type="import",
    )
    assert res == ["import modA, modB"]

def test_with_straight_imports_uncombined_standard_and_as_and_remove():
    parsed = make_parsed()
    parsed.as_map["straight"]["modA"] = ["aliasA"]
    parsed.imports["THIRDPARTY"] = {"straight": {"modA": ["some_value"]}}
    parsed.categorized_comments["above"]["straight"]["modB"] = ["# above B"]
    parsed.categorized_comments["straight"]["modB"] = ["# inline B"]

    config = Config(combine_straight_imports=False)
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["modA", "modRemove", "modB"],
        section="THIRDPARTY",
        remove_imports=["modRemove"],
        import_type="import",
    )
    assert "import modRemove" not in "".join(res)
    assert any("import modA" in line for line in res)
    assert any("import modA as aliasA" in line for line in res)
    assert any("# above B" in line for line in res)
    assert any("# inline B" in line for line in res)
