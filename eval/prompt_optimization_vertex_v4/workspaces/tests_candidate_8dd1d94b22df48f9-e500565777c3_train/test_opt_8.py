# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 77], [88, 89]]}

from unittest.mock import patch
from pathlib import Path
import pytest
from isort.hooks import git_hook
from isort.exceptions import FileSkipped

def test_git_hook_no_files():
    with patch("isort.hooks.get_lines", return_value=[]) as mock_get_lines:
        res = git_hook(lazy=True, directories=["dir1"])
        assert res == 0
        mock_get_lines.assert_called_once_with(["git", "diff-index", "--name-only", "--diff-filter=ACMRTUXB", "HEAD", "dir1"])

def test_git_hook_with_files_strict_and_modify():
    files = ["test.py", "not_python.txt", "skipped.py"]
    with patch("isort.hooks.get_lines", return_value=files) as mock_get_lines, \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n") as mock_get_output, \
         patch("isort.api.check_code_string", side_effect=[False, FileSkipped("skipped", file_path="skipped.py")]) as mock_check_code, \
         patch("isort.api.sort_file") as mock_sort_file:

        res = git_hook(strict=True, modify=True, lazy=False, settings_file="", directories=None)
        assert res == 1
        mock_get_lines.assert_called_once_with(["git", "diff-index", "--cached", "--name-only", "--diff-filter=ACMRTUXB", "HEAD"])
        mock_sort_file.assert_called_once()

def test_git_hook_non_strict():
    files = ["test.py"]
    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import a\n"), \
         patch("isort.api.check_code_string", return_value=False):

        res = git_hook(strict=False, modify=False)
        assert res == 0
