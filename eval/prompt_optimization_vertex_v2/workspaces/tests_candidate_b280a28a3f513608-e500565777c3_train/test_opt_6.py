# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 89]]}

from unittest.mock import patch
from isort.hooks import git_hook


def test_git_hook_no_files():
    with patch("isort.hooks.get_lines", return_value=[]):
        assert git_hook() == 0


def test_git_hook_non_python_file():
    with patch("isort.hooks.get_lines", return_value=["README.md"]):
        assert git_hook(strict=True) == 0


def test_git_hook_python_file_sorted_and_unsorted():
    filename = "test.py"

    with patch("isort.hooks.get_lines", return_value=[filename]), \
         patch("isort.hooks.get_output", return_value="import sys\nimport os\n"):
        # Sorted or check_code_string returning True
        with patch("isort.api.check_code_string", return_value=True):
            assert git_hook(strict=True) == 0

        # Unsorted (check_code_string returns False), strict=False
        with patch("isort.api.check_code_string", return_value=False), \
             patch("isort.api.sort_file") as mock_sort:
            assert git_hook(strict=False, modify=True, lazy=True, directories=["."], settings_file="") == 0
            mock_sort.assert_called_once_with(filename, config=mock_sort.call_args[1]["config"])

        # Unsorted, strict=True, modify=True
        with patch("isort.api.check_code_string", return_value=False), \
             patch("isort.api.sort_file") as mock_sort:
            assert git_hook(strict=True, modify=True, lazy=False, directories=None) == 1
            mock_sort.assert_called_once()
