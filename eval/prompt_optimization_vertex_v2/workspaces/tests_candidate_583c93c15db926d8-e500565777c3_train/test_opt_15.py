# file: src\sample_repo\isort\isort\hooks.py:34-93
# asked: {"lines": [34, 35, 36, 37, 38, 39, 40, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 77], [84, 87], [88, 77], [88, 89]]}
# gained: {"lines": [34, 35, 36, 37, 38, 39, 62, 63, 64, 65, 66, 68, 69, 70, 72, 73, 74, 75, 77, 78, 80, 81, 83, 84, 85, 87, 88, 89, 90, 91, 93], "branches": [[63, 64], [63, 65], [65, 66], [65, 68], [69, 70], [69, 72], [77, 78], [77, 93], [78, 77], [78, 80], [84, 87], [88, 89]]}

import os
import tempfile
from pathlib import Path
import pytest
from isort import exceptions
from isort.hooks import git_hook


def test_git_hook_no_modified_files(monkeypatch):
    monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: [])
    result = git_hook()
    assert result == 0


def test_git_hook_checks_and_modifies(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        py_file = os.path.join(tmpdir, "test_file.py")
        with open(py_file, "w", encoding="utf-8") as f:
            f.write("import sys\nimport os\n")

        monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: [py_file])
        monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import sys\nimport os\n")

        sorted_called = []
        monkeypatch.setattr("isort.api.sort_file", lambda filename, config: sorted_called.append(filename))

        result = git_hook(
            strict=True,
            modify=True,
            lazy=True,
            settings_file="",
            directories=[tmpdir],
        )

        assert result == 1
        assert py_file in sorted_called


def test_git_hook_non_python_file_and_skipped(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        txt_file = os.path.join(tmpdir, "test_file.txt")
        py_file = os.path.join(tmpdir, "test_file.py")

        monkeypatch.setattr("isort.hooks.get_lines", lambda cmd: [txt_file, py_file])
        monkeypatch.setattr("isort.hooks.get_output", lambda cmd: "import os\nimport sys\n")

        def mock_check_code_string(*args, **kwargs):
            raise exceptions.FileSkipped("Skipped", Path("test"))

        monkeypatch.setattr("isort.api.check_code_string", mock_check_code_string)

        result = git_hook(strict=False, modify=False, lazy=False)
        assert result == 0
