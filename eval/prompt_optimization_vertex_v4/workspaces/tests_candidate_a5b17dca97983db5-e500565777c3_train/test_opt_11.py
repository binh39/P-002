# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 89]]}

from unittest.mock import patch, mock_open
from pathlib import Path
from isort.hooks import git_hook
from isort import exceptions


def test_git_hook_no_files():
    with patch("isort.hooks.get_lines", return_value=[]):
        res = git_hook()
        assert res == 0


def test_git_hook_lazy_and_directories():
    with patch("isort.hooks.get_lines", return_value=[]) as mock_get_lines:
        git_hook(lazy=True, directories=["some_dir"])
        mock_get_lines.assert_called_once_with([
            "git", "diff-index", "--name-only", "--diff-filter=ACMRTUXB", "HEAD", "some_dir"
        ])


def test_git_hook_success_and_errors_strict_modify():
    files = ["test1.py", "not_python.txt", "test2.py"]
    
    def mock_get_lines(cmd):
        return files

    def mock_get_output(cmd):
        if cmd[0] == "git" and cmd[1] == "show":
            return "import b\nimport a\n"
        return ""

    with patch("isort.hooks.get_lines", side_effect=mock_get_lines), \
         patch("isort.hooks.get_output", side_effect=mock_get_output), \
         patch("isort.api.check_code_string", return_value=False) as mock_check, \
         patch("isort.api.sort_file") as mock_sort, \
         patch("builtins.open", mock_open(read_data=b"[isort]\n")) as mock_file:

        res = git_hook(strict=True, modify=True, settings_file="dummy.toml")
        assert res == 2
        assert mock_check.call_count == 2
        assert mock_sort.call_count == 2


def test_git_hook_file_skipped_exception():
    files = ["test1.py"]

    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import a\n"), \
         patch("isort.api.check_code_string", side_effect=exceptions.FileSkipped("skipped", "test1.py")) as mock_check:

        res = git_hook(strict=False, modify=False)
        assert res == 0
        assert mock_check.call_count == 1
