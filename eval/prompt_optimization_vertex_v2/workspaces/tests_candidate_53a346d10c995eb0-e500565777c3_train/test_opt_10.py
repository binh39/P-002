# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 89]]}

import pytest
from pathlib import Path
from unittest.mock import patch
from isort.hooks import git_hook
from isort import exceptions


def test_git_hook_no_files():
    with patch("isort.hooks.get_lines", return_value=[]):
        res = git_hook()
        assert res == 0


def test_git_hook_with_files_lazy_directories_strict_modify():
    files = ["test1.txt", "test2.py"]
    
    def mock_get_lines(cmd):
        assert "--cached" not in cmd
        assert "dir1" in cmd
        return files

    with patch("isort.hooks.get_lines", side_effect=mock_get_lines) as _, \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n") as mock_get_output, \
         patch("isort.api.check_code_string", return_value=False) as mock_check, \
         patch("isort.api.sort_file") as mock_sort, \
         patch("os.path.abspath", side_effect=lambda x: x):

        res = git_hook(
            strict=True,
            modify=True,
            lazy=True,
            settings_file="",
            directories=["dir1"]
        )
        assert res == 1
        assert mock_get_output.call_count == 1
        assert mock_check.call_count == 1
        assert mock_sort.call_count == 1


def test_git_hook_file_skipped_and_non_strict():
    files = ["test.py"]

    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import a\n"), \
         patch("isort.api.check_code_string", side_effect=exceptions.FileSkipped("skipped", "test.py")) as mock_check:

        res = git_hook(strict=False, modify=False, lazy=False)
        assert res == 0
        assert mock_check.call_count == 1
