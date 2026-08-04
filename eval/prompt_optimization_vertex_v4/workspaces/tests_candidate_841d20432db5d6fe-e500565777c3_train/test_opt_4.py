# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 77], [88, 89]]}

from unittest.mock import patch
from pathlib import Path
from isort.hooks import git_hook


@patch("isort.hooks.get_lines")
def test_git_hook_no_files(mock_get_lines):
    mock_get_lines.return_value = []
    result = git_hook()
    assert result == 0


@patch("isort.hooks.get_output")
@patch("isort.hooks.get_lines")
@patch("isort.api.check_code_string")
@patch("isort.api.sort_file")
def test_git_hook_all_branches(mock_sort_file, mock_check_code, mock_get_lines, mock_get_output):
    # Test combinations of lazy=True, directories=["dir"], strict=True/False, modify=True/False
    # File not ending in .py (should be skipped), and file ending in .py with check failing (error counted)
    mock_get_lines.return_value = ["README.md", "test_file.py"]
    mock_get_output.return_value = "import b\nimport a\n"
    mock_check_code.return_value = False  # Triggers error increment

    # 1. lazy=False, directories=None, strict=False, modify=False
    res = git_hook(strict=False, modify=False, lazy=False, directories=None)
    assert res == 0
    mock_check_code.assert_called()

    # 2. lazy=True, directories=["some_dir"], strict=True, modify=True
    res = git_hook(strict=True, modify=True, lazy=True, directories=["some_dir"])
    assert res == 1
    mock_sort_file.assert_called_once_with("test_file.py", config=mock_sort_file.call_args[1]["config"])
