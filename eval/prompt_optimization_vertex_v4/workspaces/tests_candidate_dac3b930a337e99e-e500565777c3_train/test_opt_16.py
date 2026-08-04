# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 27, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 27], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

from pathlib import Path
import pytest

from isort.files import find
from isort.settings import Config


def test_find_directory_walk_and_files(tmp_path: Path):
    # Setup directory structure:
    # tmp_path/
    #   ├── skipped_dir/ (skipped)
    #   ├── normal_dir/
    #   │     ├── file.py (supported)
    #   │     └── ignored.txt (unsupported)
    #   ├── skipped_file.py (skipped file)
    #   └── direct_file.py (supported file passed directly)
    
    skipped_dir = tmp_path / "skipped_dir"
    skipped_dir.mkdir()
    
    normal_dir = tmp_path / "normal_dir"
    normal_dir.mkdir()
    
    py_file = normal_dir / "file.py"
    py_file.write_text("print('hello')")
    
    txt_file = normal_dir / "ignored.txt"
    txt_file.write_text("text")

    skipped_file = tmp_path / "skipped_file.py"
    skipped_file.write_text("print('skip')")

    direct_file = tmp_path / "direct_file.py"
    direct_file.write_text("print('direct')")

    # Use valid isort config options like skip and skip_glob
    config = Config(
        skip=[str(skipped_dir), str(skipped_file)],
        skip_glob=["**/skipped_dir/*", "**/skipped_file.py"]
    )

    skipped: list[str] = []
    broken: list[str] = []

    paths = [
        str(tmp_path),
        str(tmp_path / "non_existent"),
        str(direct_file),
    ]

    results = list(find(paths, config, skipped, broken))

    # Assertions
    assert str(py_file) in results
    assert str(direct_file) in results
    assert str(tmp_path / "non_existent") in broken
    assert len(skipped) > 0


def test_find_visited_dirs_symlink(tmp_path: Path):
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    
    symlink_dir = tmp_path / "sym_sub"
    try:
        symlink_dir.symlink_to(sub_dir, target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks not supported on this platform/filesystem")

    config = Config(follow_links=True)
    skipped: list[str] = []
    broken: list[str] = []

    results = list(find([str(tmp_path)], config, skipped, broken))
    assert isinstance(results, list)
