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
        assert git_hook() == 0


def test_git_hook_lazy_and_directories():
    with patch("isort.hooks.get_lines", return_value=[]) as mock_get_lines:
        git_hook(lazy=True, directories=["dir1", "dir2"])
        called_cmd = mock_get_lines.call_args[0][0]
        assert "--cached" not in called_cmd
        assert "dir1" in called_cmd
        assert "dir2" in called_cmd


def test_git_hook_checks_and_modifies():
    files = ["test1.py", "test2.txt", "test3.py"]
    
    def mock_get_lines(cmd):
        return files

    def mock_get_output(cmd):
        return "import b\nimport a\n"

    with patch("isort.hooks.get_lines", side_effect=mock_get_lines), \
         patch("isort.hooks.get_output", side_effect=mock_get_output), \
         patch("isort.api.check_code_string", side_effect=[False, False]) as mock_check, \
         patch("isort.api.sort_file") as mock_sort, \
         patch("os.path.abspath", side_effect=lambda x: f"/abs/path/{x}"), \
         patch("os.path.exists", return_value=True):

        # Test strict=True, modify=True, non-py files ignored, py files checked/modified
        errors = git_hook(strict=True, modify=True)
        assert errors == 2
        assert mock_check.call_count == 2  # test1.py and test3.py (test2.txt ignored)
        assert mock_sort.call_count == 2
        mock_sort.assert_any_call("test1.py", config=mock_sort.call_args_list[0][1]["config"])
        mock_sort.assert_any_call("test3.py", config=mock_sort.call_args_list[1][1]["config"])


def test_git_hook_strict_false():
    files = ["test.py"]
    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n"), \
         patch("isort.api.check_code_string", return_value=False), \
         patch("isort.api.sort_file"), \
         patch("os.path.exists", return_value=True):

        errors = git_hook(strict=False, modify=False)
        assert errors == 0


def test_git_hook_file_skipped_exception():
    files = ["test.py"]
    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n"), \
         patch("isort.api.check_code_string", side_effect=exceptions.FileSkipped("skipped", Path("test.py"))), \
         patch("os.path.exists", return_value=True):

        errors = git_hook(strict=True, modify=True)
        assert errors == 0
