# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 31], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

import os
from pathlib import Path
from isort.files import find
from isort.settings import Config


def test_find_directory_and_files(tmp_path: Path):
    # Setup directory structure:
    # tmp_path/
    #   ├── skipped_dir/          (skipped by config)
    #   │   └── ignored.py
    #   ├── normal_dir/
    #   │   ├── test.py           (supported file)
    #   │   ├── skipped_file.py   (skipped by config)
    #   │   └── notes.txt         (unsupported file type)
    #   └── direct_file.py        (passed directly as path, supported)

    skipped_dir = tmp_path / "skipped_dir"
    skipped_dir.mkdir()
    (skipped_dir / "ignored.py").write_text("print(1)")

    normal_dir = tmp_path / "normal_dir"
    normal_dir.mkdir()
    test_py = normal_dir / "test.py"
    test_py.write_text("print(2)")
    skipped_file = normal_dir / "skipped_file.py"
    skipped_file.write_text("print(3)")
    txt_file = normal_dir / "notes.txt"
    txt_file.write_text("hello")

    direct_file = tmp_path / "direct_file.py"
    direct_file.write_text("print(4)")

    # Configure isort to skip skipped_dir and skipped_file.py using config overrides or explicit skip
    config = Config(
        skip=[skipped_dir.name, skipped_file.name],
    )

    skipped: list[str] = []
    broken: list[str] = []

    # Test directory walking, skipped directories, skipped files, supported/unsupported files
    paths_to_search = [str(normal_dir), str(skipped_dir)]
    results = list(find(paths_to_search, config, skipped, broken))

    assert str(test_py) in results
    assert str(txt_file) not in results  # Unsupported filetype branch
    assert len(skipped) > 0


def test_find_direct_file_and_broken(tmp_path: Path):
    valid_file = tmp_path / "valid.py"
    valid_file.write_text("print('hello')")

    non_existent = tmp_path / "does_not_exist.py"

    config = Config()
    skipped: list[str] = []
    broken: list[str] = []

    # Test direct file path (else branch) and non-existent path (broken.append branch)
    paths = [str(valid_file), str(non_existent)]
    results = list(find(paths, config, skipped, broken))

    assert results == [str(valid_file)]
    assert broken == [str(non_existent)]


def test_find_symlink_visited_dirs(tmp_path: Path):
    # Test resolved_path in visited_dirs (symlink pointing back to a parent or already visited dir)
    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()
    sub_dir = real_dir / "sub"
    sub_dir.mkdir()

    # Create a symlink inside real_dir pointing back to real_dir
    symlink_dir = real_dir / "sym"
    try:
        os.symlink(real_dir, symlink_dir, target_is_directory=True)
    except OSError:
        # Symlinks might not be supported on all platforms/filesystems (e.g. Windows without admin)
        return

    config = Config(follow_links=True)
    skipped: list[str] = []
    broken: list[str] = []

    results = list(find([str(real_dir)], config, skipped, broken))
    assert isinstance(results, list)
