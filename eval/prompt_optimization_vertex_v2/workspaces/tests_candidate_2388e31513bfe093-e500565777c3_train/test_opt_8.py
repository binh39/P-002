# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from isort.hooks import git_hook
from isort import exceptions


@patch("isort.hooks.get_lines")
def test_git_hook_no_files_modified(mock_get_lines):
    mock_get_lines.return_value = []
    
    result = git_hook(strict=True, modify=True, lazy=True, directories=["some_dir"])
    assert result == 0
    mock_get_lines.assert_called_once_with(["git", "diff-index", "--name-only", "--diff-filter=ACMRTUXB", "HEAD", "some_dir"])


@patch("isort.hooks.api.sort_file")
@patch("isort.hooks.api.check_code_string")
@patch("isort.hooks.get_output")
@patch("isort.hooks.get_lines")
def test_git_hook_with_files_and_options(
    mock_get_lines,
    mock_get_output,
    mock_check_code_string,
    mock_sort_file,
):
    mock_get_lines.return_value = ["file1.txt", "file2.py", "file3.py"]
    mock_get_output.return_value = "import b\nimport a\n"
    
    # file2.py has errors (check_code_string returns False), file3.py has no errors (True)
    mock_check_code_string.side_effect = [False, True]

    # Test with strict=False, modify=False, lazy=False, directories=None, default settings_file
    result = git_hook(strict=False, modify=False, lazy=False, settings_file="", directories=None)
    assert result == 0
    mock_get_lines.assert_called_once_with(["git", "diff-index", "--cached", "--name-only", "--diff-filter=ACMRTUXB", "HEAD"])
    assert mock_get_output.call_count == 2
    mock_check_code_string.assert_called()


@patch("isort.hooks.api.sort_file")
@patch("isort.hooks.api.check_code_string")
@patch("isort.hooks.get_output")
@patch("isort.hooks.get_lines")
def test_git_hook_strict_and_modify(
    mock_get_lines,
    mock_get_output,
    mock_check_code_string,
    mock_sort_file,
):
    mock_get_lines.return_value = ["file.py"]
    mock_get_output.return_value = "import b\nimport a\n"
    mock_check_code_string.return_value = False

    result = git_hook(strict=True, modify=True, lazy=True)
    assert result == 1
    mock_get_lines.assert_called_once_with(["git", "diff-index", "--name-only", "--diff-filter=ACMRTUXB", "HEAD"])
    mock_sort_file.assert_called_once_with("file.py", config=mock_sort_file.call_args[1]["config"])


@patch("isort.hooks.api.check_code_string")
@patch("isort.hooks.get_output")
@patch("isort.hooks.get_lines")
def test_git_hook_file_skipped_exception(
    mock_get_lines,
    mock_get_output,
    mock_check_code_string,
):
    mock_get_lines.return_value = ["file.py"]
    mock_get_output.return_value = "import a\n"
    mock_check_code_string.side_effect = exceptions.FileSkipped(file_path=Path("file.py"), message="Skipped")

    result = git_hook(strict=True, modify=True)
    assert result == 0
