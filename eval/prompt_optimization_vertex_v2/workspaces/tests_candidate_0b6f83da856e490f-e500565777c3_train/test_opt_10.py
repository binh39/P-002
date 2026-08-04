# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 89]]}

from unittest.mock import patch
from isort.hooks import git_hook


@patch("isort.hooks.get_lines")
def test_git_hook_no_files(mock_get_lines):
    mock_get_lines.return_value = []
    result = git_hook()
    assert result == 0


@patch("isort.hooks.api.sort_file")
@patch("isort.hooks.api.check_code_string")
@patch("isort.hooks.get_output")
@patch("isort.hooks.get_lines")
def test_git_hook_with_files_strict_modify(
    mock_get_lines, mock_get_output, mock_check_code, mock_sort_file
):
    mock_get_lines.return_value = ["test.py", "not_python.txt"]
    mock_get_output.return_value = "import b\nimport a\n"
    # Return False to indicate check_code_string found sorting errors
    mock_check_code.return_value = False

    result = git_hook(strict=True, modify=True, lazy=True, directories=["test.py"])
    assert result == 1
    mock_sort_file.assert_called_once_with("test.py", config=mock_check_code.call_args[1]["config"])


@patch("isort.hooks.Config")
@patch("isort.hooks.api.check_code_string")
@patch("isort.hooks.get_output")
@patch("isort.hooks.get_lines")
def test_git_hook_non_strict_no_modify(
    mock_get_lines, mock_get_output, mock_check_code, mock_config
):
    mock_get_lines.return_value = ["test.py"]
    mock_get_output.return_value = "import a\nimport b\n"
    # Return True to indicate code is sorted correctly
    mock_check_code.return_value = True

    result = git_hook(strict=False, modify=False, lazy=False, settings_file="")
    assert result == 0
