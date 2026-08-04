# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 619, 620, 621, 623, 624, 625, 628, 630, 631, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 619], [620, 621], [620, 628], [621, 623], [631, 633]]}

from isort.parse import file_contents
from isort.output import _with_straight_imports
from isort.settings import Config


def test_with_straight_imports_combine_empty():
    parsed = file_contents("", config=Config(combine_straight_imports=True))
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
    parsed = file_contents("import os\nimport sys\n", config=Config(combine_straight_imports=True))
    parsed.categorized_comments["above"]["straight"]["os"] = ["# comment os"]
    parsed.categorized_comments["straight"]["os"] = ["inline os"]
    parsed.categorized_comments["above"]["straight"]["sys"] = ["# comment sys"]
    parsed.categorized_comments["straight"]["sys"] = ["inline sys"]

    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os", "sys"],
        section="GENERAL",
        remove_imports=[],
        import_type="import",
    )
    assert "# comment os" in result
    assert "# comment sys" in result
    assert any("import os, sys" in line for line in result)
    assert any("inline os inline sys" in line for line in result)


def test_with_straight_imports_combine_without_inline_comments():
    parsed = file_contents("import os\nimport sys\n", config=Config(combine_straight_imports=True))
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




def test_with_straight_imports_standard_no_base_import_in_as_map():
    parsed = file_contents("import os as my_os\n", config=Config(combine_straight_imports=False))
    parsed.as_map["straight"]["os"] = ["my_os"]
    section_name = list(parsed.imports.keys())[0]
    parsed.imports[section_name]["straight"]["os"] = False

    config = Config(combine_straight_imports=False)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["os"],
        section=section_name,
        remove_imports=[],
        import_type="import",
    )
    assert result == ["import os as my_os"]


def test_with_straight_imports_standard_without_as_map():
    parsed = file_contents("import math\n", config=Config(combine_straight_imports=False))
    section_name = list(parsed.imports.keys())[0]
    config = Config(combine_straight_imports=False)
    result = _with_straight_imports(
        parsed=parsed,
        config=config,
        straight_modules=["math"],
        section=section_name,
        remove_imports=[],
        import_type="import",
    )
    assert result == ["import math"]
