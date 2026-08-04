# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 89]]}

from pathlib import Path
import pytest
from isort.hooks import git_hook


def test_git_hook_no_files_modified(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: [])
    assert git_hook() == 0


def test_git_hook_lazy_and_directories_and_modify_and_strict(monkeypatch, tmp_path):
    settings_file = tmp_path / "some_settings.toml"
    settings_file.write_text("[isort]\n")

    commands_run = []

    def mock_get_lines(cmd):
        commands_run.append(cmd)
        return ["test_file.py", "not_python.txt"]

    monkeypatch.setattr("isort.hooks.get_lines", mock_get_lines)
    monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import z\nimport a\n")

    checked = []
    sorted_files = []

    monkeypatch.setattr("isort.api.check_code_string", lambda code, file_path, config: (checked.append((code, file_path, config)) or False))
    monkeypatch.setattr("isort.api.sort_file", lambda filename, config: sorted_files.append(filename))

    ret = git_hook(
        strict=True,
        modify=True,
        lazy=True,
        settings_file=str(settings_file),
        directories=["dir1", "dir2"]
    )

    assert ret == 1
    assert "--cached" not in commands_run[0]
    assert "dir1" in commands_run[0]
    assert "dir2" in commands_run[0]
    assert len(checked) == 1
    assert sorted_files == ["test_file.py"]
