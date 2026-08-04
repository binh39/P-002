# file: src\sample_repo\isort\isort\wrap_modes.py:47-85
# asked: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 65, 66, 67, 68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 80, 82, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 65], [61, 84], [66, 67], [66, 72], [68, 69], [68, 71]]}
# gained: {"lines": [47, 48, 49, 50, 52, 53, 54, 55, 56, 57, 58, 59, 62, 63, 84, 85], "branches": [[49, 50], [49, 52], [53, 54], [53, 85], [61, 84]]}

import pytest
from isort.wrap_modes import grid


def test_grid_empty_imports():
    interface = {
        "imports": [],
        "statement": "from module import",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
        "white_space": "    ",
        "include_trailing_comma": False,
    }
    assert grid(**interface) == ""


def test_grid_normal_flow_and_trailing_comma():
    # Exercises:
    # - `if not interface["imports"]:` (False)
    # - `while interface["imports"]:` loop
    # - `if len(next_statement.split(...) ...) > interface["line_length"]:` (False -> line 84 `else`)
    # - `include_trailing_comma=True`
    interface = {
        "imports": ["a", "b"],
        "statement": "from module import ",
        "comments": [],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 80,
        "white_space": "    ",
        "include_trailing_comma": True,
    }
    res = grid(**interface)
    assert res == "from module import (a, b,)"


def test_grid_long_next_statement_and_long_import_parts():
    # Exercises:
    # - Line 61 `if` condition True (long next_statement)
    # - Line 66-71 loop over parts of `next_import` (`for part in next_import.split(" ")[1:]`)
    # - Line 68 `if len(new_line) + 1 > interface["line_length"]:` (both True and False branches)
    # - Comment handling and resetting `interface["comments"] = []`
    interface = {
        "imports": ["very_long_import_name_that_exceeds_line_length part2_which_is_also_very_long"],
        "statement": "from module import ",
        "comments": ["# some comment"],
        "remove_comments": False,
        "comment_prefix": "#",
        "line_separator": "\n",
        "line_length": 30,
        "white_space": "    ",
        "include_trailing_comma": False,
    }
    res = grid(**interface)
    # Ensure that it executed without error and produced a valid string wrapping it.
    assert res.startswith("from module import (")
    assert res.endswith(")")
    assert "very_long_import_name_that_exceeds_line_length" in res
