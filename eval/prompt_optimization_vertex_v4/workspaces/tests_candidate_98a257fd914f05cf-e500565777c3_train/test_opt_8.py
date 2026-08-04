# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 29], [31, 16], [31, 32], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

from pathlib import Path
import os
import pytest
from isort.settings import Config
from isort.files import find

def test_find_directory_and_files(tmp_path: Path):
    # Setup directory structure
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    skipped_dir = tmp_path / "skipped_dir"
    skipped_dir.mkdir()

    # Create files
    py_file = tmp_path / "test.py"
    py_file.write_text("print(1)")
    
    sub_py_file = sub_dir / "sub.py"
    sub_py_file.write_text("print(2)")

    skipped_file = sub_dir / "skipped.py"
    skipped_file.write_text("print(3)")

    # isort Config skip matches basename or relative path depending on settings,
    # so we explicitly configure skip with the filename or use a skip list that isort checks.
    config = Config(skip=["skipped.py", "skipped_dir"])
    
    skipped: list[str] = []
    broken: list[str] = []

    results = list(find([str(tmp_path)], config, skipped, broken))

    # Assertions
    assert str(py_file) in results
    assert str(sub_py_file) in results
    assert str(skipped_file) not in results

def test_find_broken_and_direct_file(tmp_path: Path):
    py_file = tmp_path / "direct.py"
    py_file.write_text("print(4)")

    config = Config()
    skipped: list[str] = []
    broken: list[str] = []

    paths = [str(py_file), "non_existent_path_xyz"]
    results = list(find(paths, config, skipped, broken))

    assert results == [str(py_file)]
    assert "non_existent_path_xyz" in broken

def test_find_symlink_visited_dirs(tmp_path: Path):
    # Test directory loop / resolved_path in visited_dirs (if follow_links=True)
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "test.py").write_text("print(5)")

    link_dir = tmp_path / "link"
    try:
        os.symlink(real_dir, link_dir, target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks not supported on this platform/environment")

    config = Config(follow_links=True)
    skipped: list[str] = []
    broken: list[str] = []

    results = list(find([str(real_dir), str(link_dir)], config, skipped, broken))
    assert len(results) >= 1
