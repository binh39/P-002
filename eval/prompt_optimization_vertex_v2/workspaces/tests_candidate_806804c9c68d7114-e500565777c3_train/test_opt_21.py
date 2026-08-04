# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 77]]}

from pathlib import Path
from unittest.mock import patch
import pytest

from isort.exceptions import FileSkipped
from isort.hooks import git_hook


def test_git_hook_no_files_modified():
    with patch("isort.hooks.get_lines", return_value=[]):
        assert git_hook() == 0


def test_git_hook_files_modified_no_py_files():
    with patch("isort.hooks.get_lines", return_value=["README.md", "script.sh"]):
        assert git_hook() == 0


def test_git_hook_with_lazy_and_directories():
    with patch("isort.hooks.get_lines", return_value=[]) as mock_get_lines:
        git_hook(lazy=True, directories=["src", "tests"])
        mock_get_lines.assert_called_once_with(
            ["git", "diff-index", "--name-only", "--diff-filter=ACMRTUXB", "HEAD", "src", "tests"]
        )




def test_git_hook_non_strict_no_modify():
    files = ["file1.py"]
    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n"), \
         patch("isort.api.check_code_string", return_value=False), \
         patch("isort.api.sort_file") as mock_sort_file, \
         patch("os.path.abspath", side_effect=lambda x: x), \
         patch("os.path.dirname", return_value="."):

        result = git_hook(strict=False, modify=False)
        assert result == 0
        mock_sort_file.assert_not_called()


def test_git_hook_file_skipped_exception():
    files = ["file1.py"]
    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import a\n"), \
         patch("isort.api.check_code_string", side_effect=FileSkipped("file1.py", Path("file1.py"))), \
         patch("os.path.abspath", side_effect=lambda x: x), \
         patch("os.path.dirname", return_value="."):

        result = git_hook(strict=True)
        assert result == 0
