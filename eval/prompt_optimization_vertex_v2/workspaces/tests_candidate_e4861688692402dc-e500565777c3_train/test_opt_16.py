# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613], "branches": [[585, 586], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611]]}

import pytest
from isort.parse import file_contents
from isort.output import _with_straight_imports
from isort.settings import Config


def test_with_straight_imports_combine_empty():
    parsed = file_contents("", Config())
    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(parsed, config, [], "ungrouped", [], "import")
    assert result == []


def test_with_straight_imports_combine_with_comments():
    parsed = file_contents("import os\nimport sys\n", Config())
    parsed.categorized_comments["above"]["straight"]["os"] = ["# OS comment"]
    parsed.categorized_comments["straight"]["os"] = ["inline os"]
    parsed.categorized_comments["above"]["straight"]["sys"] = ["# SYS comment"]
    
    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(parsed, config, ["os", "sys"], "ungrouped", [], "import")
    
    assert result == [
        "# OS comment",
        "# SYS comment",
        "import os, sys  # inline os",
    ]


def test_with_straight_imports_combine_without_inline_comments():
    parsed = file_contents("import os\nimport sys\n", Config())
    config = Config(combine_straight_imports=True)
    result = _with_straight_imports(parsed, config, ["os", "sys"], "ungrouped", [], "import")
    assert result == ["import os, sys"]




