# file: src\sample_repo\isort\isort\output.py:572-643
# asked: {"lines": [572, 573, 574, 575, 576, 577, 578, 579, 580, 582, 585, 586, 587, 589, 590, 592, 593, 594, 595, 596, 598, 599, 600, 602, 604, 606, 607, 608, 611, 613, 615, 616, 617, 619, 620, 621, 622, 623, 624, 625, 628, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [586, 589], [592, 593], [592, 598], [593, 594], [593, 595], [595, 592], [595, 596], [599, 600], [599, 602], [606, 607], [606, 611], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [620, 628], [621, 622], [621, 623], [631, 632], [631, 633]]}
# gained: {"lines": [572, 580, 582, 585, 586, 587, 615, 616, 617, 619, 620, 621, 622, 623, 625, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640, 643], "branches": [[585, 586], [585, 615], [586, 587], [615, 616], [615, 643], [616, 617], [616, 619], [620, 621], [621, 622], [631, 632], [631, 633]]}

import pytest
from isort.output import _with_straight_imports
from isort import parse
from isort.settings import Config
from isort.comments import add_to_line as with_comments

@pytest.fixture
def parsed_content():
    return parse.ParsedContent(
        in_lines=["import os", "import sys"],
        lines_without_imports=[""],
        import_index=0,
        place_imports={},
        import_placements={},
        as_map={"straight": {"os": [], "sys": []}},
        imports={"default": {"straight": {"os": True, "sys": True}}},
        categorized_comments={"above": {"straight": {}}, "straight": {}},
        change_count=0,
        original_line_count=2,
        line_separator="\n",
        sections=None,
        verbose_output=[],
        trailing_commas=set()
    )

@pytest.fixture
def config():
    return Config(combine_straight_imports=True)

def test_with_no_straight_modules(parsed_content, config):
    straight_modules = []
    remove_imports = []
    output = _with_straight_imports(parsed_content, config, straight_modules, "default", remove_imports, "import")
    assert output == []

def test_with_straight_modules_no_as_imports(parsed_content, config):
    straight_modules = ["os", "sys"]
    remove_imports = []
    output = _with_straight_imports(parsed_content, config, straight_modules, "default", remove_imports, "import")
    assert output == ["import os", "import sys"]

def test_with_straight_modules_with_above_comments(parsed_content, config):
    parsed_content.categorized_comments["above"]["straight"]["os"] = ["# This is os"]
    straight_modules = ["os"]
    remove_imports = []
    output = _with_straight_imports(parsed_content, config, straight_modules, "default", remove_imports, "import")
    assert output == ["# This is os", "import os"]

def test_with_straight_modules_with_inline_comments(parsed_content, config):
    parsed_content.categorized_comments["straight"]["os"] = ["# Inline comment for os"]
    straight_modules = ["os"]
    remove_imports = []
    output = _with_straight_imports(parsed_content, config, straight_modules, "default", remove_imports, "import")
    expected_output = [with_comments(parsed_content.categorized_comments["straight"]["os"], "import os", removed=config.ignore_comments, comment_prefix=config.comment_prefix)]
    assert output == expected_output


def test_with_remove_imports(parsed_content, config):
    straight_modules = ["os", "sys"]
    remove_imports = ["os"]
    output = _with_straight_imports(parsed_content, config, straight_modules, "default", remove_imports, "import")
    assert output == ["import sys"]

