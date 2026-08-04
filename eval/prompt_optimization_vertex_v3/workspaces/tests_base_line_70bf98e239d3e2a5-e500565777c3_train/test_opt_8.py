# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 89]]}

from pathlib import Path
from unittest.mock import patch, mock_open
from isort.hooks import git_hook
from isort.exceptions import FileSkipped


def test_git_hook_no_files():
    with patch("isort.hooks.get_lines", return_value=[]):
        res = git_hook()
        assert res == 0


def test_git_hook_files_no_py():
    with patch("isort.hooks.get_lines", return_value=["README.md"]):
        res = git_hook()
        assert res == 0


def test_git_hook_check_and_modify_and_lazy_and_strict_and_directories():
    mock_files = ["test_file.py"]
    
    def mock_get_lines(cmd):
        assert "--cached" not in cmd
        assert "some_dir" in cmd
        return mock_files

    with patch("isort.hooks.get_lines", side_effect=mock_get_lines), \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n"), \
         patch("isort.api.check_code_string", return_value=False), \
         patch("isort.api.sort_file") as mock_sort, \
         patch("builtins.open", mock_open(read_data=b"")):

        res = git_hook(
            strict=True,
            modify=True,
            lazy=True,
            settings_file="some_settings.toml",
            directories=["some_dir"],
        )
        assert res == 1
        mock_sort.assert_called_once()


def test_git_hook_file_skipped_exception():
    mock_files = ["test_file.py"]

    with patch("isort.hooks.get_lines", return_value=mock_files), \
         patch("isort.hooks.get_output", return_value="import a\n"), \
         patch("isort.api.check_code_string", side_effect=FileSkipped("skipped", "test_file.py")) as mock_check:

        res = git_hook(strict=True)
        assert res == 0
        mock_check.assert_called_once()
