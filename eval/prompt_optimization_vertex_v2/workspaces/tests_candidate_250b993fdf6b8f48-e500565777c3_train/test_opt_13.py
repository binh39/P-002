# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 89]]}

from pathlib import Path
import pytest
from isort.hooks import git_hook
from isort.exceptions import FileSkipped


def test_git_hook_no_files_modified(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: [])
    assert git_hook() == 0


def test_git_hook_with_files_lazy_and_directories(monkeypatch):
    called_cmds = []

    def mock_get_lines(cmd):
        called_cmds.append(cmd)
        return ["test_file.py"]

    monkeypatch.setattr("isort.hooks.get_lines", mock_get_lines)
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import b\nimport a\n")
    monkeypatch.setattr("isort.api.check_code_string", lambda contents, file_path, config: False)

    sorted_files = []
    monkeypatch.setattr("isort.api.sort_file", lambda filename, config: sorted_files.append(filename))

    # Test with lazy=True and directories provided, strict=True, modify=True
    res = git_hook(
        strict=True,
        modify=True,
        lazy=True,
        settings_file="",
        directories=["src"],
    )

    assert res == 1
    assert "--cached" not in called_cmds[0]
    assert "src" in called_cmds[0]
    assert sorted_files == ["test_file.py"]


def test_git_hook_strict_false_and_skipped_file(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: ["skipped.py"])
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import b\nimport a\n")

    def mock_check_code_string(*args, **kwargs):
        raise FileSkipped("Skipped", "skipped.py")

    monkeypatch.setattr("isort.api.check_code_string", mock_check_code_string)

    res = git_hook(strict=False, modify=False)
    assert res == 0


def test_git_hook_not_python_file(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: ["readme.txt"])
    # get_output should not be called for non-py files
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: (_ for _ in ()).throw(AssertionError("Should not call")))

    res = git_hook(strict=True)
    assert res == 0
