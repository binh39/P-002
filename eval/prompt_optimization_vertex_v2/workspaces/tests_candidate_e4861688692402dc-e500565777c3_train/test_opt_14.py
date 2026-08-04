# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 89]]}

from pathlib import Path
import pytest
from isort import hooks, exceptions


def test_git_hook_no_files_modified(monkeypatch):
    monkeypatch.setattr(hooks, "get_lines", lambda cmd: [])
    result = hooks.git_hook()
    assert result == 0


def test_git_hook_with_files_sorted_and_unsorted(monkeypatch):
    py_file = "test.py"
    txt_file = "readme.txt"

    monkeypatch.setattr(hooks, "get_lines", lambda cmd: [py_file, txt_file])
    monkeypatch.setattr(hooks, "get_output", lambda cmd: "import b\nimport a\n")

    # non-strict, modify=False -> returns 0
    res = hooks.git_hook(strict=False, modify=False, lazy=True, directories=["src"], settings_file="")
    assert res == 0

    # strict=True, modify=True -> returns 1 (error found)
    sorted_called = []
    monkeypatch.setattr(hooks.api, "sort_file", lambda fn, config: sorted_called.append(fn))
    monkeypatch.setattr(hooks.api, "check_code_string", lambda code, file_path, config: False)

    res_strict = hooks.git_hook(strict=True, modify=True, lazy=False, settings_file="")
    assert res_strict == 1
    assert sorted_called == [py_file]


def test_git_hook_file_skipped(monkeypatch):
    py_file = "skipped.py"

    monkeypatch.setattr(hooks, "get_lines", lambda cmd: [py_file])
    monkeypatch.setattr(hooks, "get_output", lambda cmd: "import b\nimport a\n")

    def mock_check(*args, **kwargs):
        raise exceptions.FileSkipped("skipped", Path("skipped.py"))

    monkeypatch.setattr(hooks.api, "check_code_string", mock_check)

    res = hooks.git_hook(strict=True)
    assert res == 0
