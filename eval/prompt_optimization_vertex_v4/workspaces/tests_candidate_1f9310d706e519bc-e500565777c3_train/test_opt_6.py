# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

import os
from pathlib import Path
import pytest
from isort.files import find
from isort.settings import Config


def test_find_directory_walk_and_files(tmp_path):
    # Setup directory structure:
    # tmp_path/
    #   ├── normal_dir/
    #   │     └── file.py
    #   ├── skipped_dir/
    #   │     └── file.py
    #   ├── supported.py
    #   └── skipped_file.py
    
    normal_dir = tmp_path / "normal_dir"
    normal_dir.mkdir()
    py_in_normal = normal_dir / "file.py"
    py_in_normal.write_text("print(1)\n")

    skipped_dir = tmp_path / "skipped_dir"
    skipped_dir.mkdir()
    py_in_skipped = skipped_dir / "file.py"
    py_in_skipped.write_text("print(2)\n")

    supported_file = tmp_path / "supported.py"
    supported_file.write_text("print(3)\n")

    skipped_file = tmp_path / "skipped_file.py"
    skipped_file.write_text("print(4)\n")

    # Config that skips specific dirs/files (using base names or relative patterns for isort to pick up via is_skipped)
    config = Config(
        skip=["skipped_dir", "skipped_file.py"],
    )

    skipped = []
    broken = []
    
    # Test passing a directory path
    results = list(find([str(tmp_path)], config, skipped, broken))

    # Assertions
    assert str(py_in_normal) in results
    assert str(supported_file) in results
    assert str(py_in_skipped) not in results
    assert str(skipped_file) not in results
    assert len(skipped) > 0
    assert broken == []


def test_find_visited_dirs_deduplication(tmp_path):
    # This tests the branch: if resolved_path in visited_dirs
    # We can pass duplicate paths or symlinks (or paths that resolve to the same location)
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    py_file = sub_dir / "file.py"
    py_file.write_text("print(1)\n")

    config = Config()
    skipped = []
    broken = []

    # Pass the same directory twice in paths, or directory and its resolved form
    results = list(find([str(tmp_path), str(tmp_path.resolve())], config, skipped, broken))

    assert str(py_file) in results
    assert broken == []


def test_find_broken_path():
    config = Config()
    skipped = []
    broken = []
    non_existent = "/non/existent/path/that/definitely/does/not/exist/12345"

    results = list(find([non_existent], config, skipped, broken))

    assert results == []
    assert broken == [non_existent]
    assert skipped == []


def test_find_direct_file_path(tmp_path):
    config = Config()
    skipped = []
    broken = []
    
    single_file = tmp_path / "test.py"
    single_file.write_text("x = 1\n")

    results = list(find([str(single_file)], config, skipped, broken))

    assert results == [str(single_file)]
    assert skipped == []
    assert broken == []
