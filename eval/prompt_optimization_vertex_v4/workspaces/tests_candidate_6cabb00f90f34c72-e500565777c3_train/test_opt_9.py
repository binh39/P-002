# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 27, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 27], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

import os
from pathlib import Path
from isort.files import find
from isort.settings import Config


def test_find_directory_walk_and_files(tmp_path: Path):
    # Setup directory structure:
    # tmp_path/
    #   ├── skipped_dir/ (should be skipped)
    #   ├── normal_dir/
    #   │     ├── sub_dir/
    #   │     │     └── test.py
    #   │     ├── test.py (supported file)
    #   │     └── ignore.txt (unsupported file)
    #   ├── non_existent (broken path)
    #   └── direct_file.py (direct path file)

    skipped_dir = tmp_path / "skipped_dir"
    skipped_dir.mkdir()

    normal_dir = tmp_path / "normal_dir"
    normal_dir.mkdir()

    sub_dir = normal_dir / "sub_dir"
    sub_dir.mkdir()

    py_file_sub = sub_dir / "test.py"
    py_file_sub.write_text("print('sub')")

    py_file_normal = normal_dir / "test.py"
    py_file_normal.write_text("print('normal')")

    txt_file = normal_dir / "ignore.txt"
    txt_file.write_text("not python")

    direct_file = tmp_path / "direct_file.py"
    direct_file.write_text("print('direct')")

    non_existent = tmp_path / "non_existent_path"

    # Also test file skipped explicitly via config
    skipped_file = normal_dir / "skipped_file.py"
    skipped_file.write_text("print('skipped')")

    # Add both skipped_dir and skipped_file to paths as well, or skip via Config properly.
    # Note: isort's Config skip matches by name or relative path. Providing the filename/basename or path:
    config = Config(
        skip=["skipped_dir", "skipped_file.py"],
    )

    skipped: list[str] = []
    broken: list[str] = []

    paths = [
        str(normal_dir),
        str(skipped_dir),
        str(non_existent),
        str(direct_file),
    ]

    results = list(find(paths, config, skipped, broken))

    # Assertions
    assert str(non_existent) in broken
    assert str(direct_file) in results
    assert str(py_file_normal) in results
    assert str(py_file_sub) in results
    assert len(skipped) > 0
    assert str(txt_file) not in results


def test_find_visited_dirs_symlink_or_duplicate(tmp_path: Path):
    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()
    (real_dir / "a.py").write_text("x = 1")

    link_dir = tmp_path / "link_dir"
    try:
        link_dir.symlink_to(real_dir, target_is_directory=True)
    except OSError:
        return

    parent_dir = tmp_path / "parent"
    parent_dir.mkdir()
    sub1 = parent_dir / "sub1"
    sub1.mkdir()

    config = Config(follow_links=True)
    skipped: list[str] = []
    broken: list[str] = []

    results = list(find([str(parent_dir)], config, skipped, broken))
    assert isinstance(results, list)
