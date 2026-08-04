# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 89]]}

from pathlib import Path
import pytest
from isort import exceptions
from isort.hooks import git_hook


def test_git_hook_no_files(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: [])
    assert git_hook() == 0


def test_git_hook_with_files_no_py_strict(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: ["README.md"])
    assert git_hook(strict=True) == 0


def test_git_hook_lazy_and_directories(monkeypatch):
    captured_cmds = []

    def mock_get_lines(cmd):
        captured_cmds.append(cmd)
        return ["test.py"]

    monkeypatch.setattr("isort.hooks.get_lines", mock_get_lines)
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import b\nimport a\n")
    monkeypatch.setattr("isort.api.check_code_string", lambda contents, file_path, config: False)
    monkeypatch.setattr("isort.api.sort_file", lambda filename, config: None)

    errors = git_hook(
        strict=True,
        modify=True,
        lazy=True,
        directories=["src"],
        settings_file="",
    )
    assert errors == 1
    assert "--cached" not in captured_cmds[0]
    assert "src" in captured_cmds[0]


def test_git_hook_file_skipped(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: ["test.py"])
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import a\n")

    def mock_check_code_string(*args, **kwargs):
        raise exceptions.FileSkipped("Skipped", Path("test.py"))

    monkeypatch.setattr("isort.api.check_code_string", mock_check_code_string)

    assert git_hook(strict=False) == 0
