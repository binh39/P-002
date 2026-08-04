# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 77], [88, 89]]}

from pathlib import Path
from unittest.mock import patch
import pytest

from isort.hooks import git_hook
from isort import exceptions


def test_git_hook_no_files_modified():
    with patch("isort.hooks.get_lines", return_value=[]):
        res = git_hook()
        assert res == 0


def test_git_hook_lazy_and_directories():
    # Covers lazy=True, directories=['src'], files with .py and non-.py, check code string failing, modify=True, strict=True/False
    with patch("isort.hooks.get_lines", return_value=["test.py", "README.md", "bad.py"]) as mock_get_lines, \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n") as mock_get_output, \
         patch("isort.api.check_code_string", side_effect=[False, False]) as mock_check, \
         patch("isort.api.sort_file") as mock_sort:
        
        # Call with lazy=True and directories=['dir']
        res = git_hook(strict=False, modify=True, lazy=True, directories=["dir"])
        assert res == 0
        
        # Verify diff_cmd construction via get_lines call args
        called_diff_cmd = mock_get_lines.call_args[0][0]
        assert "--cached" not in called_diff_cmd
        assert "dir" in called_diff_cmd

        # Reset mock_sort call count for strict test call where modify=False
        mock_sort.reset_mock()

        # Check strict=True returns errors count
        mock_check.side_effect = [False, False]
        res_strict = git_hook(strict=True, modify=False, lazy=False)
        assert res_strict == 2
        assert mock_sort.call_count == 0


def test_git_hook_file_skipped_exception():
    # Covers the exception handler for exceptions.FileSkipped
    with patch("isort.hooks.get_lines", return_value=["skipped.py"]), \
         patch("isort.hooks.get_output", return_value="import a\n"), \
         patch("isort.api.check_code_string", side_effect=exceptions.FileSkipped("skipped", Path("skipped.py"))):
        
        res = git_hook(strict=True)
        assert res == 0
