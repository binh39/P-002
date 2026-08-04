# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 89]]}

from unittest.mock import patch
from pathlib import Path
from isort.hooks import git_hook
from isort import exceptions


def test_git_hook_no_files():
    with patch("isort.hooks.get_lines", return_value=[]):
        assert git_hook() == 0


def test_git_hook_non_py_files():
    with patch("isort.hooks.get_lines", return_value=["readme.txt"]):
        assert git_hook(strict=True) == 0


def test_git_hook_py_file_well_sorted_strict_false():
    with patch("isort.hooks.get_lines", return_value=["test.py"]):
        with patch("isort.hooks.get_output", return_value="import os\n"):
            with patch("isort.api.check_code_string", return_value=True):
                assert git_hook(strict=False, modify=False, lazy=True, directories=["test.py"]) == 0


def test_git_hook_py_file_unsorted_strict_true_modify_true():
    with patch("isort.hooks.get_lines", return_value=["test.py"]):
        with patch("isort.hooks.get_output", return_value="import sys\nimport os\n"):
            with patch("isort.api.check_code_string", return_value=False):
                with patch("isort.api.sort_file") as mock_sort:
                    assert git_hook(strict=True, modify=True) == 1
                    mock_sort.assert_called_once()


def test_git_hook_file_skipped_exception():
    with patch("isort.hooks.get_lines", return_value=["test.py"]):
        with patch("isort.hooks.get_output", return_value="import sys\nimport os\n"):
            with patch("isort.api.check_code_string", side_effect=exceptions.FileSkipped("skipped", "test.py")):
                assert git_hook(strict=True, modify=True) == 0
