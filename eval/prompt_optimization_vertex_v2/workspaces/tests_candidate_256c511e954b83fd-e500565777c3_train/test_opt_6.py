# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 89]]}

import pytest
from pathlib import Path
from unittest.mock import patch
from isort.hooks import git_hook
from isort import exceptions


def test_git_hook_no_files():
    with patch("isort.hooks.get_lines", return_value=[]):
        res = git_hook(strict=True, modify=True, lazy=True, settings_file="some_settings", directories=["dir1"])
        assert res == 0


@patch("isort.hooks.api.sort_file")
@patch("isort.hooks.api.check_code_string", return_value=False)
@patch("isort.hooks.get_output", return_value="import b\nimport a\n")
@patch("isort.hooks.get_lines", return_value=["test.py"])
def test_git_hook_errors_strict_modify(mock_get_lines, mock_get_output, mock_check, mock_sort):
    res = git_hook(strict=True, modify=True, lazy=False, directories=None)
    assert res == 1
    mock_sort.assert_called_once_with("test.py", config=mock_check.call_args[1]["config"])


@patch("isort.hooks.api.check_code_string", return_value=True)
@patch("isort.hooks.get_output", return_value="import a\nimport b\n")
@patch("isort.hooks.get_lines", return_value=["test.py", "not_python.txt"])
def test_git_hook_no_errors_non_strict(mock_get_lines, mock_get_output, mock_check):
    res = git_hook(strict=False, modify=False, lazy=True, directories=["test.py"])
    assert res == 0
    # only test.py (ends with .py) should trigger check_code_string
    mock_check.assert_called_once()


@patch("isort.hooks.api.check_code_string", side_effect=exceptions.FileSkipped("skipped", Path("test.py")))
@patch("isort.hooks.get_output", return_value="import b\nimport a\n")
@patch("isort.hooks.get_lines", return_value=["test.py"])
def test_git_hook_file_skipped(mock_get_lines, mock_get_output, mock_check):
    res = git_hook(strict=True, modify=False, lazy=False)
    assert res == 0
