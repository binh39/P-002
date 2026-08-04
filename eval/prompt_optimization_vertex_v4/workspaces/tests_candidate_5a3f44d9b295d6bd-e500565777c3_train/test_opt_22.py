# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 77], [88, 89]]}

from pathlib import Path
from unittest.mock import patch
from isort.hooks import git_hook
from isort import exceptions

def test_git_hook_no_files():
    with patch("isort.hooks.get_lines", return_value=[]):
        res = git_hook()
        assert res == 0

def test_git_hook_with_files_and_options(tmp_path):
    d = tmp_path / "dir1"
    d.mkdir()
    settings_file = tmp_path / "dummy.toml"
    settings_file.write_text("")

    files = ["test.py", "not_python.txt", "unsorted.py"]
    
    def mock_get_lines(cmd):
        return files

    def mock_get_output(cmd):
        if cmd[1] == "show":
            return "import b\nimport a\n"
        return ""

    with patch("isort.hooks.get_lines", side_effect=mock_get_lines), \
         patch("isort.hooks.get_output", side_effect=mock_get_output), \
         patch("isort.api.check_code_string", return_value=False), \
         patch("isort.api.sort_file") as mock_sort:

        # Test strict=False, modify=False, lazy=False, directories=None
        res = git_hook(strict=False, modify=False, lazy=False, settings_file="", directories=None)
        assert res == 0
        mock_sort.assert_not_called()

        # Test strict=True, modify=True, lazy=True, directories=["dir1"]
        res = git_hook(strict=True, modify=True, lazy=True, settings_file=str(settings_file), directories=["dir1"])
        assert res == 2  # Two .py files with check_code_string returning False
        assert mock_sort.call_count == 2

def test_git_hook_file_skipped():
    files = ["skipped.py"]
    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n"), \
         patch("isort.api.check_code_string", side_effect=exceptions.FileSkipped("skipped", "skipped.py")):
        res = git_hook(strict=True)
        assert res == 0
