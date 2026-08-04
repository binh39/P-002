# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 89]]}

from pathlib import Path
import pytest
from isort import exceptions
from isort.hooks import git_hook


def test_git_hook_no_files_modified(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: [])
    result = git_hook()
    assert result == 0


def test_git_hook_with_lazy_and_directories(monkeypatch):
    called_cmds = []

    def mock_get_lines(cmd):
        called_cmds.append(cmd)
        return ["test.py"]

    monkeypatch.setattr("isort.hooks.get_lines", mock_get_lines)
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import b\nimport a\n")
    monkeypatch.setattr("isort.api.check_code_string", lambda contents, file_path, config: False)

    # Track sort_file calls
    sorted_files = []
    monkeypatch.setattr("isort.api.sort_file", lambda filename, config: sorted_files.append(filename))

    result = git_hook(strict=True, modify=True, lazy=True, directories=["dir1"])
    
    assert result == 1
    assert "--cached" not in called_cmds[0]
    assert "dir1" in called_cmds[0]
    assert sorted_files == ["test.py"]


def test_git_hook_non_python_file_and_check_passes(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: ["README.md", "clean.py"])
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "print('hello')")
    
    # check_code_string returns True (meaning no isort errors)
    checked_files = []
    monkeypatch.setattr(
        "isort.api.check_code_string",
        lambda contents, file_path, config: checked_files.append(file_path) or True
    )

    result = git_hook(strict=False)
    assert result == 0
    # README.md should be skipped because it doesn't end with .py
    assert len(checked_files) == 1
    assert checked_files[0].name == "clean.py"


def test_git_hook_file_skipped_exception(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: ["skipped.py"])
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import a\n")

    def mock_check(*args, **kwargs):
        raise exceptions.FileSkipped("Skipped", Path("skipped.py"))

    monkeypatch.setattr("isort.api.check_code_string", mock_check)

    result = git_hook(strict=True)
    assert result == 0
