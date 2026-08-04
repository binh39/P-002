# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 77], [88, 89]]}

from unittest.mock import patch
from pathlib import Path
from isort.hooks import git_hook
from isort.exceptions import FileSkipped

def test_git_hook_no_files():
    with patch("isort.hooks.get_lines", return_value=[]):
        assert git_hook() == 0

def test_git_hook_staged_and_unstaged_combinations(tmp_path):
    settings_file = tmp_path / "some_settings.toml"
    settings_file.write_text("")

    files = ["test1.py", "not_python.txt", "test2.py"]
    
    # Mock subprocess calls / helpers
    with patch("isort.hooks.get_lines", return_value=files) as mock_get_lines, \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n") as mock_get_output, \
         patch("isort.api.check_code_string", side_effect=[False, False]) as mock_check, \
         patch("isort.api.sort_file") as mock_sort:

        # Test case 1: lazy=True, directories provided, strict=True, modify=True
        res = git_hook(
            strict=True,
            modify=True,
            lazy=True,
            settings_file=str(settings_file),
            directories=["dir1", "dir2"]
        )
        
        # Verify diff_cmd construction
        called_diff_cmd = mock_get_lines.call_args[0][0]
        assert "--cached" not in called_diff_cmd
        assert "dir1" in called_diff_cmd
        assert "dir2" in called_diff_cmd
        
        # Verify errors are counted (2 .py files, both return False from check_code_string)
        assert res == 2
        assert mock_check.call_count == 2
        assert mock_sort.call_count == 2

def test_git_hook_file_skipped_exception():
    files = ["test_skip.py"]
    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import a\n"), \
         patch("isort.api.check_code_string", side_effect=FileSkipped("skipped", "test_skip.py")) as mock_check, \
         patch("isort.api.sort_file") as mock_sort:

        res = git_hook(strict=True, modify=True)
        assert res == 0
        mock_sort.assert_not_called()

def test_git_hook_non_strict_returns_zero():
    files = ["test_non_strict.py"]
    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n"), \
         patch("isort.api.check_code_string", return_value=False):

        res = git_hook(strict=False, modify=False)
        assert res == 0
