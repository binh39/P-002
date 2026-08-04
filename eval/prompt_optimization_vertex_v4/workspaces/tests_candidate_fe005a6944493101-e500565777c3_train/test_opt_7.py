# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 89]]}

from pathlib import Path
import pytest
from isort import hooks, exceptions


def test_git_hook_no_files(monkeypatch):
    monkeypatch.setattr(hooks, "get_lines", lambda cmd: [])
    result = hooks.git_hook()
    assert result == 0


def test_git_hook_non_py_files(monkeypatch):
    monkeypatch.setattr(hooks, "get_lines", lambda cmd: ["README.md"])
    result = hooks.git_hook(strict=True)
    assert result == 0


def test_git_hook_py_file_well_sorted(monkeypatch, tmp_path):
    py_file = tmp_path / "test.py"
    py_file.write_text("import os\nimport sys\n")

    monkeypatch.setattr(hooks, "get_lines", lambda cmd: [str(py_file)])
    monkeypatch.setattr(hooks, "get_output", lambda cmd: "import os\nimport sys\n")

    result = hooks.git_hook(strict=True)
    assert result == 0


def test_git_hook_py_file_unsorted_strict_and_modify(monkeypatch, tmp_path):
    py_file = tmp_path / "test.py"
    py_file.write_text("import sys\nimport os\n")

    monkeypatch.setattr(hooks, "get_lines", lambda cmd: [str(py_file)], raising=True)
    monkeypatch.setattr(hooks, "get_output", lambda cmd: "import sys\nimport os\n")

    sorted_called = []
    monkeypatch.setattr(hooks.api, "sort_file", lambda filename, config: sorted_called.append(filename))

    result = hooks.git_hook(strict=True, modify=True, lazy=True, directories=["some_dir"])
    assert result == 1
    assert sorted_called == [str(py_file)]


def test_git_hook_file_skipped(monkeypatch, tmp_path):
    py_file = tmp_path / "test.py"
    py_file.write_text("import sys\nimport os\n")

    monkeypatch.setattr(hooks, "get_lines", lambda cmd: [str(py_file)])
    monkeypatch.setattr(hooks, "get_output", lambda cmd: "import sys\nimport os\n")

    def mock_check_code(*args, **kwargs):
        raise exceptions.FileSkipped("Skipped", Path("test.py"))

    monkeypatch.setattr(hooks.api, "check_code_string", mock_check_code)

    result = hooks.git_hook(strict=True)
    assert result == 0
