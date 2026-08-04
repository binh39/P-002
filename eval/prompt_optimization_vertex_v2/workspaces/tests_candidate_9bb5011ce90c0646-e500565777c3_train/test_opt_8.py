# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 77], [88, 89]]}

from unittest.mock import patch, mock_open
from pathlib import Path
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


def test_git_hook_non_python_file():
    with patch("isort.hooks.get_lines", return_value=["readme.txt"]):
        assert git_hook() == 0


def test_git_hook_check_fails_strict_no_modify():
    files = ["test.py"]
    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n"), \
         patch("isort.api.check_code_string", return_value=False) as mock_check, \
         patch("isort.api.sort_file") as mock_sort:
        
        ret = git_hook(strict=True, modify=False)
        assert ret == 1
        mock_check.assert_called_once()
        mock_sort.assert_not_called()


def test_git_hook_check_fails_modify_non_strict():
    files = ["test.py"]
    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n"), \
         patch("isort.api.check_code_string", return_value=False), \
         patch("isort.api.sort_file") as mock_sort, \
         patch("builtins.open", mock_open(read_data="[isort]\n")):
        
        ret = git_hook(strict=False, modify=True, settings_file="some_config.cfg")
        assert ret == 0
        mock_sort.assert_called_once_with("test.py", config=mock_sort.call_args[1]["config"])


def test_git_hook_file_skipped_exception():
    files = ["test.py"]
    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import a\n"), \
         patch("isort.api.check_code_string", side_effect=exceptions.FileSkipped("skipped", Path("test.py"))):
        
        ret = git_hook(strict=True)
        assert ret == 0
