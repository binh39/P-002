# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}

from pathlib import Path
import pytest
from isort import exceptions
from isort.hooks import git_hook


def test_git_hook_no_files_modified(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: [])
    result = git_hook()
    assert result == 0


def test_git_hook_with_files_sorted_and_unsorted(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: ["test1.py", "test2.py", "not_py.txt"])
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "print(1)\n")

    checked_files = []
    sorted_files = []

    def mock_check_code_string(content, file_path, config):
        checked_files.append(str(file_path))
        # Return False (unsorted) for test1.py, True (sorted) for test2.py
        if "test1.py" in str(file_path):
            return False
        return True

    monkeypatch.setattr("isort.api.check_code_string", mock_check_code_string)
    monkeypatch.setattr("isort.api.sort_file", lambda fn, config: sorted_files.append(fn))

    # Test with strict=False, modify=False
    res = git_hook(strict=False, modify=False, lazy=True, directories=["dir1"])
    assert res == 0
    assert "test1.py" in checked_files
    assert "test2.py" in checked_files
    assert len(sorted_files) == 0

    # Test with strict=True, modify=True
    checked_files.clear()
    res_strict = git_hook(strict=True, modify=True, lazy=False)
    assert res_strict == 1
    assert sorted_files == ["test1.py"]


def test_git_hook_file_skipped(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: ["skipped.py"])
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "content")

    def mock_check_code_string(content, file_path, config):
        raise exceptions.FileSkipped("Skipped", Path("skipped.py"))

    monkeypatch.setattr("isort.api.check_code_string", mock_check_code_string)

    res = git_hook(strict=True, modify=True)
    assert res == 0
