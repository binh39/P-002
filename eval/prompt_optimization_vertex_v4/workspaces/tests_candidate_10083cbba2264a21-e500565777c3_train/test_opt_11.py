# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}

import os
from pathlib import Path
from unittest.mock import patch
from isort.hooks import git_hook
from isort.exceptions import FileSkipped

def test_git_hook_no_files():
    with patch("isort.hooks.get_lines", return_value=[]):
        assert git_hook() == 0

def test_git_hook_lazy_and_directories():
    with patch("isort.hooks.get_lines", return_value=[]) as mock_get_lines:
        git_hook(lazy=True, directories=["dir1", "dir2"])
        mock_get_lines.assert_called_once_with([
            "git", "diff-index", "--name-only", "--diff-filter=ACMRTUXB", "HEAD", "dir1", "dir2"
        ])

def test_git_hook_checks_and_modifies(tmp_path):
    config_file = tmp_path / ".isort.cfg"
    config_file.write_text("[isort]\nprofile = black\n")

    files = ["not_python.txt", "file1.py", "file2.py"]
    
    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n"), \
         patch("isort.api.check_code_string", side_effect=[False, True]) as mock_check, \
         patch("isort.api.sort_file") as mock_sort:
        
        # strict=False, modify=True
        res = git_hook(strict=False, modify=True, settings_file=str(config_file))
        assert res == 0
        assert mock_check.call_count == 2
        mock_sort.assert_called_once_with("file1.py", config=mock_check.call_args_list[0].kwargs["config"])

def test_git_hook_strict_errors():
    files = ["file1.py"]
    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n"), \
         patch("isort.api.check_code_string", return_value=False), \
         patch("isort.api.sort_file") as mock_sort:
        
        res = git_hook(strict=True, modify=False)
        assert res == 1
        mock_sort.assert_not_called()

def test_git_hook_file_skipped_exception():
    files = ["file1.py"]
    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n"), \
         patch("isort.api.check_code_string", side_effect=FileSkipped("skipped", "file1.py")):
        
        res = git_hook(strict=True)
        assert res == 0
