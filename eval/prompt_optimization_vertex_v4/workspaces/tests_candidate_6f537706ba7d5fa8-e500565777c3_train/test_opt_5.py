# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 80], [84, 87], [88, 77], [88, 89]]}

from pathlib import Path
import pytest
from isort import exceptions
from isort.hooks import git_hook


def test_git_hook_no_modified_files(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: [])
    result = git_hook()
    assert result == 0


def test_git_hook_files_checked_and_sorted(monkeypatch, tmp_path):
    py_file = tmp_path / "test_sample.py"
    py_file.write_text("import z\nimport a\n")

    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: [str(py_file)])
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import z\nimport a\n")

    # check_code_string returns False when code is not sorted properly
    monkeypatch.setattr("isort.api.check_code_string", lambda content, file_path, config: False)

    sorted_called = []
    monkeypatch.setattr("isort.api.sort_file", lambda filename, config: sorted_called.append(filename))

    # Test with modify=False, strict=False -> returns 0
    assert git_hook(strict=False, modify=False, lazy=True, directories=[str(tmp_path)]) == 0
    assert len(sorted_called) == 0

    # Test with modify=True, strict=True -> returns error count (1)
    assert git_hook(strict=True, modify=True, lazy=False, settings_file="") == 1
    assert sorted_called == [str(py_file)]


def test_git_hook_file_skipped_exception(monkeypatch, tmp_path):
    py_file = tmp_path / "skipped.py"
    py_file.write_text("import b\nimport a\n")

    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: [str(py_file)])
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import b\nimport a\n")

    def mock_check_code(*args, **kwargs):
        raise exceptions.FileSkipped("Skipped", Path("skipped.py"))

    monkeypatch.setattr("isort.api.check_code_string", mock_check_code)

    result = git_hook(strict=True)
    assert result == 0
