# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 89]]}

from pathlib import Path
from unittest.mock import patch
import pytest
from isort.hooks import git_hook
from isort.exceptions import FileSkipped

def test_git_hook_no_files_modified():
    with patch("isort.hooks.get_lines", return_value=[]):
        assert git_hook() == 0

def test_git_hook_check_errors_and_modify_and_lazy_and_directories():
    mock_files = ["test1.py", "not_py.txt", "test2.py"]
    
    def mock_get_lines(cmd):
        assert "--cached" not in cmd
        assert "dir1" in cmd
        return mock_files

    def mock_get_output(cmd):
        return "import b\nimport a\n"

    with patch("isort.hooks.get_lines", side_effect=mock_get_lines), \
         patch("isort.hooks.get_output", side_effect=mock_get_output), \
         patch("isort.api.check_code_string", side_effect=[False, False]), \
         patch("isort.api.sort_file") as mock_sort, \
         patch("isort.Config.__init__", return_value=None):
        
        ret = git_hook(
            strict=True,
            modify=True,
            lazy=True,
            settings_file="some_settings.py",
            directories=["dir1"]
        )
        assert ret == 2
        assert mock_sort.call_count == 2

def test_git_hook_file_skipped_exception():
    mock_files = ["test1.py"]
    
    with patch("isort.hooks.get_lines", return_value=mock_files), \
         patch("isort.hooks.get_output", return_value="import a\n"), \
         patch("isort.api.check_code_string", side_effect=FileSkipped("skipped", "test1.py")):
        
        ret = git_hook(strict=False, modify=False)
        assert ret == 0
