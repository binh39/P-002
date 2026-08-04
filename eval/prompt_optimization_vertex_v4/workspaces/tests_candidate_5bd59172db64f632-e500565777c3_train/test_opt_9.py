# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 77], [88, 89]]}

from pathlib import Path
from unittest.mock import patch
from isort.hooks import git_hook
from isort.exceptions import FileSkipped

def test_git_hook_no_files_modified():
    with patch("isort.hooks.get_lines", return_value=[]):
        assert git_hook() == 0

def test_git_hook_staged_vs_lazy():
    # Test lazy=True and directories provided
    with patch("isort.hooks.get_lines", return_value=[]) as mock_get_lines:
        git_hook(lazy=True, directories=["subdir"])
        called_cmd = mock_get_lines.call_args[0][0]
        assert "--cached" not in called_cmd
        assert "subdir" in called_cmd

def test_git_hook_checks_and_modifies():
    files = ["test.py", "ignored.txt"]
    
    def mock_get_lines(cmd):
        if "--cached" in cmd:
            return files
        return files

    with patch("isort.hooks.get_lines", side_effect=mock_get_lines), \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n"), \
         patch("isort.api.check_code_string", return_value=False) as mock_check, \
         patch("isort.api.sort_file") as mock_sort:
        
        # Test strict=True, modify=True
        errors = git_hook(strict=True, modify=True)
        assert errors == 1
        mock_check.assert_called_once()
        mock_sort.assert_called_once_with("test.py", config=mock_check.call_args[1]["config"])

def test_git_hook_strict_false():
    files = ["test.py"]
    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import a\nimport b\n"), \
         patch("isort.api.check_code_string", return_value=False):
        
        # strict=False should return 0 even if errors > 0
        assert git_hook(strict=False, modify=False) == 0

def test_git_hook_file_skipped_exception():
    files = ["test.py"]
    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import a\n"), \
         patch("isort.api.check_code_string", side_effect=FileSkipped("skipped", "test.py")):
        
        assert git_hook(strict=True) == 0
