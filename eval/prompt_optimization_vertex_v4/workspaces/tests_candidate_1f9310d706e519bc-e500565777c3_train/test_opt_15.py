# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 77], [88, 89]]}

from unittest.mock import patch
from pathlib import Path
from isort.hooks import git_hook
from isort import exceptions


def test_git_hook_no_files():
    with patch("isort.hooks.get_lines", return_value=[]):
        assert git_hook() == 0


def test_git_hook_lazy_and_directories():
    with patch("isort.hooks.get_lines", return_value=[]) as mock_get_lines:
        git_hook(lazy=True, directories=["src"])
        mock_get_lines.assert_called_once_with([
            "git", "diff-index", "--name-only", "--diff-filter=ACMRTUXB", "HEAD", "src"
        ])


def test_git_hook_non_py_file():
    with patch("isort.hooks.get_lines", return_value=["README.md"]):
        assert git_hook(strict=True) == 0


def test_git_hook_check_error_no_modify():
    with patch("isort.hooks.get_lines", return_value=["test.py"]), \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n"), \
         patch("isort.api.check_code_string", return_value=False), \
         patch("isort.api.sort_file") as mock_sort_file:
        
        assert git_hook(strict=False, modify=False) == 0
        mock_sort_file.assert_not_called()

        assert git_hook(strict=True, modify=False) == 1
        mock_sort_file.assert_not_called()


def test_git_hook_check_error_with_modify():
    with patch("isort.hooks.get_lines", return_value=["test.py"]), \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n"), \
         patch("isort.api.check_code_string", return_value=False), \
         patch("isort.api.sort_file") as mock_sort_file:
        
        assert git_hook(strict=True, modify=True) == 1
        mock_sort_file.assert_called_once()


def test_git_hook_file_skipped_exception():
    with patch("isort.hooks.get_lines", return_value=["test.py"]), \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n"), \
         patch("isort.api.check_code_string", side_effect=exceptions.FileSkipped("skipped", "test.py")):
        
        assert git_hook(strict=True) == 0
