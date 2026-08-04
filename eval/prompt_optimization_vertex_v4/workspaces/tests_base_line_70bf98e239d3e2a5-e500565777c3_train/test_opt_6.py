# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

import os
from pathlib import Path
from isort.files import find
from isort.settings import Config


def test_find_all_branches(tmp_path: Path) -> None:
    # Setup directory structure and files
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()
    
    skipped_dir = tmp_path / "skipped_dir"
    skipped_dir.mkdir()

    py_file = sub_dir / "test.py"
    py_file.write_text("print(1)\n")

    skipped_py_file = sub_dir / "skipped.py"
    skipped_py_file.write_text("print(2)\n")

    txt_file = sub_dir / "notes.txt"
    txt_file.write_text("hello\n")

    # Direct file path
    direct_file = tmp_path / "direct.py"
    direct_file.write_text("print(3)\n")

    # Non-existent path
    broken_path = tmp_path / "does_not_exist.py"

    # Config setup using exact filenames/basenames for skip or setting absolute paths
    # As seen in isort Config.is_skipped, basenames or absolute matching work.
    config = Config(
        skip=["skipped_dir", "skipped.py"],
        follow_links=True,
    )

    skipped: list[str] = []
    broken: list[str] = []

    paths = [
        str(tmp_path),             # triggers os.path.isdir branch, os.walk, directory skipping, file skipping, supported filetype
        str(broken_path),          # triggers not os.path.exists branch -> broken
        str(direct_file),          # triggers else branch (path is file directly)
    ]

    results = list(find(paths, config, skipped, broken))

    # Assertions
    assert str(py_file) in results
    assert str(direct_file) in results
    assert str(txt_file) not in results  # not supported filetype
    assert any("skipped.py" in s for s in skipped)
    assert any("skipped_dir" in s for s in skipped)
    assert str(broken_path) in broken


def test_find_visited_dirs_symlink(tmp_path: Path) -> None:
    # Test resolved_path in visited_dirs (symlink pointing to an already visited directory)
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "a.py").write_text("x = 1\n")

    link_dir = tmp_path / "link"
    try:
        os.symlink(real_dir, link_dir, target_is_directory=True)
    except OSError:
        # Symlinks might not be supported on some platforms (e.g. Windows without admin privileges)
        return

    config = Config(follow_links=True)
    skipped: list[str] = []
    broken: list[str] = []

    results = list(find([str(tmp_path)], config, skipped, broken))
    assert len(results) >= 1
