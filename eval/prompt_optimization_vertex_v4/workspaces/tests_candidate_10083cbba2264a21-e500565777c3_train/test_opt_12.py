# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [631, 632], [631, 633]]}

from isort import parse
from isort.output import _with_straight_imports
from isort.settings import Config


def _create_dummy_parsed():
    return parse.file_contents("", config=Config())


def test_with_straight_imports_combine_empty():
    config = Config(combine_straight_imports=True)
    parsed = _create_dummy_parsed()
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
    config = Config(combine_straight_imports=True)
    parsed = _create_dummy_parsed()
    parsed.categorized_comments["above"]["straight"]["os"] = ["# OS comment"]
    parsed.categorized_comments["straight"]["sys"] = ["inline comment"]

    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "sys"],
        section="STDLIB",
        remove_imports=[],
        import_type="import",
    )
    assert res == ["# OS comment", "import os, sys  # inline comment"]


def test_with_straight_imports_combine_without_inline():
    config = Config(combine_straight_imports=True)
    parsed = _create_dummy_parsed()
    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "sys"],
        section="STDLIB",
        remove_imports=[],
        import_type="import",
    )
    assert res == ["import os, sys"]


def test_with_straight_imports_normal_flow():
    config = Config(combine_straight_imports=False)
    parsed = _create_dummy_parsed()
    parsed.as_map["straight"]["os"] = ["os_alias"]
    parsed.imports["STDLIB"]["straight"]["os"] = True

    parsed.categorized_comments["above"]["straight"]["sys"] = ["# sys above"]
    parsed.categorized_comments["straight"]["sys"] = ["sys inline"]

    res = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["removed_mod", "os", "sys"],
        section="STDLIB",
        remove_imports=["removed_mod"],
        import_type="import",
    )
    assert any("os as os_alias" in line for line in res)
    assert any("sys" in line for line in res)
