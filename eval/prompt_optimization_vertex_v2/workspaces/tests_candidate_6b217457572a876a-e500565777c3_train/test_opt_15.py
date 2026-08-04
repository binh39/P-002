# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 89]]}

from unittest.mock import patch
from pathlib import Path
from isort.hooks import git_hook


def test_git_hook_no_files():
    with patch("isort.hooks.get_lines", return_value=[]):
        assert git_hook() == 0


def test_git_hook_files_no_python():
    with patch("isort.hooks.get_lines", return_value=["README.md", "data.json"]):
        assert git_hook(strict=True) == 0


def test_git_hook_python_file_sorted_strict_false():
    with patch("isort.hooks.get_lines", return_value=["test.py"]), \
         patch("isort.hooks.get_output", return_value="import os\nimport sys\n"), \
         patch("isort.api.check_code_string", return_value=True), \
         patch("os.path.abspath", return_value="/abs/path/test.py"), \
         patch("os.path.exists", return_value=True), \
         patch("isort.settings._find_config", return_value=("/abs/path", {})):
        assert git_hook(strict=False, modify=False, lazy=True, directories=["test.py"]) == 0


def test_git_hook_python_file_unsorted_strict_true_modify_true():
    with patch("isort.hooks.get_lines", return_value=["test.py"]), \
         patch("isort.hooks.get_output", return_value="import sys\nimport os\n"), \
         patch("isort.api.check_code_string", return_value=False), \
         patch("isort.api.sort_file") as mock_sort_file, \
         patch("os.path.abspath", return_value="/abs/path/test.py"), \
         patch("os.path.exists", return_value=True), \
         patch("isort.settings._find_config", return_value=("/abs/path", {})):
        
        res = git_hook(strict=True, modify=True)
        assert res == 1
        mock_sort_file.assert_called_once()
        args, kwargs = mock_sort_file.call_args
        assert args[0] == "test.py"
