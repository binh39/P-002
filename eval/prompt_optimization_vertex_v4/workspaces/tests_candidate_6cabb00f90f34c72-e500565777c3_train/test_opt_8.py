# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}

import subprocess
from pathlib import Path
import pytest
from isort import exceptions
from isort.hooks import git_hook


def test_git_hook_no_files(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: [])
    assert git_hook() == 0


def test_git_hook_with_files_unmodified_and_modified(monkeypatch, tmp_path):
    # Create a temporary python file
    p = tmp_path / "test_file.py"
    p.write_text("import b\nimport a\n")

    files = [str(p)]

    # Mock get_lines to return our file
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: files)

    # Mock get_output to return code string
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import b\nimport a\n")

    # Test when code needs sorting, strict=False, modify=False
    # Should return 0 because strict=False
    assert git_hook(strict=False, modify=False) == 0

    # Test strict=True, modify=False -> should return 1 error
    assert git_hook(strict=True, modify=False) == 1

    # Test strict=True, modify=True -> should sort and return 1 (or 0 errors? wait, check_code_string still returns False because check is done before sorting, then sort_file is called)
    assert git_hook(strict=True, modify=True) == 1


def test_git_hook_options_and_exceptions(monkeypatch, tmp_path):
    p = tmp_path / "test_file.py"
    p.write_text("import a\nimport b\n")  # correctly sorted

    files = [str(p)]

    captured_cmds = []

    def mock_get_lines(cmd):
        captured_cmds.append(cmd)
        return files

    monkeypatch.setattr("isort.hooks.get_lines", mock_get_lines)
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import a\nimport b\n")

    # Test lazy=True and directories provided
    res = git_hook(lazy=True, directories=["some_dir"], strict=True)
    assert res == 0
    assert "--cached" not in captured_cmds[0]
    assert "some_dir" in captured_cmds[0]

    # Test FileSkipped exception handling
    def mock_check_code_string(*args, **kwargs):
        raise exceptions.FileSkipped("skipped", Path("test_file.py"))

    monkeypatch.setattr("isort.api.check_code_string", mock_check_code_string)
    assert git_hook(strict=True) == 0
