# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 29, 31, 32, 33, 34, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 37], [38, 39], [38, 41]]}

import os
from pathlib import Path
import tempfile
import pytest

from isort.files import find
from isort.settings import Config


def test_find_all_branches(tmp_path):
    # Setup directories and files
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()

    skipped_dir = tmp_path / "skipped_dir"
    skipped_dir.mkdir()

    py_file = tmp_path / "test.py"
    py_file.write_text("print(1)")

    unsupported_file = tmp_path / "test.txt"
    unsupported_file.write_text("hello")

    sub_py_file = sub_dir / "sub_test.py"
    sub_py_file.write_text("print(2)")

    skipped_py_file = skipped_dir / "skip_test.py"
    skipped_py_file.write_text("print(3)")

    # Test symlink / visited_dirs coverage if supported on platform (e.g. follow_links=True)
    symlink_dir = tmp_path / "symlink_dir"
    try:
        symlink_dir.symlink_to(sub_dir, target_is_directory=True)
        has_symlink = True
    except (OSError, NotImplementedError):
        has_symlink = False

    config = Config(
        skip=[os.path.basename(skipped_dir)],
        follow_links=True,
    )

    skipped: list[str] = []
    broken: list[str] = []

    non_existent = str(tmp_path / "does_not_exit.py")

    paths = [
        str(tmp_path),
        non_existent,
        str(py_file),
    ]

    found_files = list(find(paths, config, skipped, broken))

    # Assertions
    assert str(py_file) in found_files
    assert str(sub_py_file) in found_files
    assert non_existent in broken
    assert len(skipped) > 0
