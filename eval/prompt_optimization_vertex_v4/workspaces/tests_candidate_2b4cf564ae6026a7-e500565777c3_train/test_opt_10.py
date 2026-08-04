# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 77], [88, 89]]}

from unittest.mock import patch
from pathlib import Path
from isort.hooks import git_hook
from isort import exceptions


def test_git_hook_no_files():
    with patch("isort.hooks.get_lines", return_value=[]):
        assert git_hook() == 0


def test_git_hook_staged_files_no_py_and_py_files(tmp_path):
    # Create a temporary python file so path operations work correctly
    py_file = tmp_path / "test.py"
    py_file.write_text("import b\nimport a\n")

    files = ["README.md", str(py_file)]

    def mock_get_lines(cmd):
        return files

    def mock_get_output(cmd):
        # Return contents that need sorting (returns False for check_code_string)
        return "import b\nimport a\n"

    with patch("isort.hooks.get_lines", side_effect=mock_get_lines), \
         patch("isort.hooks.get_output", side_effect=mock_get_output), \
         patch("isort.api.sort_file") as mock_sort_file:

        # Test with lazy=True, directories=['some_dir'], modify=False, strict=False
        result = git_hook(
            strict=False,
            modify=False,
            lazy=True,
            directories=["some_dir"]
        )
        assert result == 0
        mock_sort_file.assert_not_called()


def test_git_hook_strict_and_modify(tmp_path):
    py_file = tmp_path / "test.py"
    py_file.write_text("import b\nimport a\n")

    files = [str(py_file)]

    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n"), \
         patch("isort.api.sort_file") as mock_sort_file:

        result = git_hook(
            strict=True,
            modify=True,
            lazy=False,
            settings_file=""
        )
        # strict=True returns number of errors (1 error here)
        assert result == 1
        mock_sort_file.assert_called_once()


def test_git_hook_file_skipped_exception(tmp_path):
    py_file = tmp_path / "test.py"
    py_file.write_text("import b\nimport a\n")

    files = [str(py_file)]

    with patch("isort.hooks.get_lines", return_value=files), \
         patch("isort.hooks.get_output", return_value="import b\nimport a\n"), \
         patch("isort.api.check_code_string", side_effect=exceptions.FileSkipped("skipped", Path(py_file))):

        result = git_hook(strict=True, modify=True)
        assert result == 0
