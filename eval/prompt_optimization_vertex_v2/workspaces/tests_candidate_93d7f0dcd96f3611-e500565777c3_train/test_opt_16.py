# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 65, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 90, 91, 93], "branches": [[63, 65], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80]]}

from pathlib import Path
import pytest
from isort.hooks import git_hook


def test_git_hook_no_files(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: [])
    assert git_hook() == 0


def test_git_hook_non_py_files(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: ["readme.txt"])
    # Should not call get_output or check code for non-.py files
    assert git_hook(strict=True) == 0


def test_git_hook_py_file_sorted(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: ["test.py"])
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import os\nimport sys\n")

    assert git_hook(strict=True) == 0
    assert git_hook(strict=False) == 0




def test_git_hook_file_skipped(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: ["test.py"])
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import sys\nimport os\n")

    from isort import exceptions

    def mock_check_code(*args, **kwargs):
        raise exceptions.FileSkipped("Skipped", "test.py")

    monkeypatch.setattr("isort.api.check_code_string", mock_check_code)

    assert git_hook(strict=True) == 0
