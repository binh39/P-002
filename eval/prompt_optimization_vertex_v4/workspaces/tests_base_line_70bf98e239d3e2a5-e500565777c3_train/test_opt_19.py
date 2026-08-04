# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 89]]}

from unittest.mock import patch
from pathlib import Path
from isort.hooks import git_hook
from isort.exceptions import FileSkipped


def test_git_hook_no_files():
    with patch("isort.hooks.get_lines", return_value=[]):
        assert git_hook() == 0


def test_git_hook_non_python_file():
    with patch("isort.hooks.get_lines", return_value=["README.md"]):
        assert git_hook() == 0


def test_git_hook_sorted_python_file(tmp_path):
    py_file = tmp_path / "test.py"
    py_file.write_text("import os\nimport sys\n")

    with patch("isort.hooks.get_lines", return_value=[str(py_file)]):
        with patch("isort.hooks.get_output", return_value="import os\nimport sys\n"):
            assert git_hook(strict=True) == 0


def test_git_hook_unsorted_strict_and_modify(tmp_path):
    py_file = tmp_path / "test.py"
    py_file.write_text("import sys\nimport os\n")

    with patch("isort.hooks.get_lines", return_value=[str(py_file)]) as mock_get_lines:
        with patch("isort.hooks.get_output", return_value="import sys\nimport os\n"):
            with patch("isort.api.sort_file") as mock_sort_file:
                # Test with lazy=True, directories specified, modify=True, strict=True
                res = git_hook(
                    strict=True,
                    modify=True,
                    lazy=True,
                    settings_file="",
                    directories=[str(tmp_path)],
                )
                assert res == 1
                mock_sort_file.assert_called_once_with(str(py_file), config=mock_sort_file.call_args[1]["config"])
                # Check that lazy removed '--cached' and directories were extended
                called_cmd = mock_get_lines.call_args[0][0]
                assert "--cached" not in called_cmd
                assert str(tmp_path) in called_cmd


def test_git_hook_file_skipped(tmp_path):
    py_file = tmp_path / "test.py"
    py_file.write_text("import sys\nimport os\n")

    with patch("isort.hooks.get_lines", return_value=[str(py_file)]):
        with patch("isort.hooks.get_output", return_value="import sys\nimport os\n"):
            with patch("isort.api.check_code_string", side_effect=FileSkipped("skipped", str(py_file))):
                assert git_hook(strict=True) == 0
