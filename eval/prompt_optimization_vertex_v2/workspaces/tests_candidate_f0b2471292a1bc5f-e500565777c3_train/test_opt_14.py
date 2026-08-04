# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}

from pathlib import Path
import pytest
from isort.hooks import git_hook


def test_git_hook_no_files_modified(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: [])
    assert git_hook() == 0


def test_git_hook_non_python_file(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: ["README.md"])
    assert git_hook(strict=True) == 0


def test_git_hook_python_file_no_errors(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: ["test.py"])
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import os\nimport sys\n")
    monkeypatch.setattr("isort.api.check_code_string", lambda code, file_path, config: True)

    assert git_hook(strict=True) == 0
    assert git_hook(strict=False) == 0


def test_git_hook_python_file_with_errors_non_strict(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: ["test.py"])
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import sys\nimport os\n")
    monkeypatch.setattr("isort.api.check_code_string", lambda code, file_path, config: False)

    assert git_hook(strict=False) == 0


def test_git_hook_python_file_with_errors_strict_and_modify(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: ["test.py"])
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import sys\nimport os\n")
    monkeypatch.setattr("isort.api.check_code_string", lambda code, file_path, config: False)

    sorted_files = []
    monkeypatch.setattr("isort.api.sort_file", lambda filename, config: sorted_files.append(filename))

    assert git_hook(
        strict=True,
        modify=True,
        lazy=True,
        directories=["src"],
        settings_file="",
    ) == 1
    assert sorted_files == ["test.py"]
