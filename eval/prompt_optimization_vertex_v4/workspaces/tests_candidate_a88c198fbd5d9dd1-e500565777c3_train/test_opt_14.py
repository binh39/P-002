# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 89]]}

from unittest.mock import patch, MagicMock
from pathlib import Path
from isort.hooks import git_hook
from isort import exceptions


@patch("isort.hooks.get_lines")
def test_git_hook_no_files(mock_get_lines):
    mock_get_lines.return_value = []
    assert git_hook() == 0


@patch("isort.hooks.get_output")
@patch("isort.hooks.get_lines")
@patch("isort.api.check_code_string")
@patch("isort.api.sort_file")
def test_git_hook_all_branches(mock_sort_file, mock_check_code, mock_get_lines, mock_get_output, tmp_path):
    py_file = tmp_path / "test_sample.py"
    py_file.write_text("import b\nimport a\n")
    txt_file = tmp_path / "readme.txt"

    # Test when files_modified is empty with lazy=True and directories provided
    mock_get_lines.return_value = []
    assert git_hook(lazy=True, directories=["dir1"]) == 0

    # Test with python and non-python files, strict=True, modify=True, lazy=True, directories provided
    mock_get_lines.return_value = [str(py_file), str(txt_file)]
    mock_get_output.return_value = "import b\nimport a\n"
    mock_check_code.return_value = False  # Triggers error increment and modify

    res = git_hook(strict=True, modify=True, lazy=True, directories=[str(tmp_path)])
    assert res == 1
    mock_sort_file.assert_called_once()

    # Test FileSkipped exception handling and strict=False returning 0
    mock_sort_file.reset_mock()
    mock_check_code.side_effect = exceptions.FileSkipped("skipped", str(py_file))
    res2 = git_hook(strict=False, modify=False, lazy=False, settings_file="")
    assert res2 == 0
