# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 89]]}

from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
from isort.hooks import git_hook
from isort import exceptions


@patch("isort.hooks.get_lines")
def test_git_hook_no_modified_files(mock_get_lines):
    mock_get_lines.return_value = []
    result = git_hook()
    assert result == 0
    mock_get_lines.assert_called_once_with([
        "git", "diff-index", "--cached", "--name-only", "--diff-filter=ACMRTUXB", "HEAD"
    ])


@patch("isort.hooks.get_lines")
@patch("isort.hooks.get_output")
@patch("isort.api.check_code_string")
@patch("isort.api.sort_file")
def test_git_hook_with_files_and_options(
    mock_sort_file, mock_check_code, mock_get_output, mock_get_lines
):
    mock_get_lines.return_value = ["test.py", "README.md"]
    mock_get_output.return_value = "import b\nimport a\n"
    
    # check_code_string returns False (meaning it needs sorting / has error)
    mock_check_code.return_value = False

    with tempfile.TemporaryDirectory() as tmpdir:
        settings_file = Path(tmpdir) / "some_settings.toml"
        settings_file.write_text("[isort]\nprofile = 'black'\n")

        # Test with lazy=True, directories=["dir"], strict=True, modify=True
        result = git_hook(
            strict=True,
            modify=True,
            lazy=True,
            settings_file=str(settings_file),
            directories=["dir"],
        )

    assert result == 1
    mock_get_lines.assert_called_once_with([
        "git", "diff-index", "--name-only", "--diff-filter=ACMRTUXB", "HEAD", "dir"
    ])
    mock_get_output.assert_called_once_with(["git", "show", ":test.py"])
    mock_check_code.assert_called_once()
    mock_sort_file.assert_called_once_with("test.py", config=mock_check_code.call_args[1]["config"])


@patch("isort.hooks.get_lines")
@patch("isort.hooks.get_output")
@patch("isort.api.check_code_string")
@patch("isort.api.sort_file")
def test_git_hook_file_skipped_exception(
    mock_sort_file, mock_check_code, mock_get_output, mock_get_lines
):
    mock_get_lines.return_value = ["skipped.py"]
    mock_get_output.return_value = "import a\n"
    mock_check_code.side_effect = exceptions.FileSkipped("Skipped", Path("skipped.py"))

    result = git_hook(strict=False, modify=True)
    assert result == 0
    mock_check_code.assert_called_once()
    mock_sort_file.assert_not_called()
