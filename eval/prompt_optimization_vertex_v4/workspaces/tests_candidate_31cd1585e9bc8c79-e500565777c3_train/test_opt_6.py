# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 77], [88, 89]]}

from pathlib import Path
import pytest
from isort.hooks import git_hook

def test_git_hook_no_files_modified(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: [])
    assert git_hook() == 0

def test_git_hook_with_files_checked_and_modified(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: ["test_file.py", "not_py.txt"])
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import z\nimport a\n")

    checked = []
    sorted_files = []

    monkeypatch.setattr("isort.api.check_code_string", lambda content, file_path, config: (checked.append(file_path), False)[1])
    monkeypatch.setattr("isort.api.sort_file", lambda filename, config: sorted_files.append(filename))

    # Test with strict=False, modify=True, lazy=True, directories=['foo'], settings_file='dummy'
    res = git_hook(strict=False, modify=True, lazy=True, settings_file="", directories=["foo"])
    assert res == 0
    assert len(checked) == 1
    assert sorted_files == ["test_file.py"]

def test_git_hook_strict_mode_with_errors(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: ["test_file.py"])
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import z\nimport a\n")
    monkeypatch.setattr("isort.api.check_code_string", lambda content, file_path, config: False)

    res = git_hook(strict=True, modify=False, lazy=False)
    assert res == 1

def test_git_hook_file_skipped_exception(monkeypatch):
    from isort import exceptions
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: ["test_file.py"])
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import z\nimport a\n")

    def raise_skipped(*args, **kwargs):
        raise exceptions.FileSkipped("skipped", Path("test_file.py"))

    monkeypatch.setattr("isort.api.check_code_string", raise_skipped)

    res = git_hook(strict=True, modify=True, lazy=False)
    assert res == 0
