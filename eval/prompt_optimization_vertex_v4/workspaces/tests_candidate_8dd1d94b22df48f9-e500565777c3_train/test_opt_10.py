# file: src\sample_repo\isort\isort\files.py:8-41
# asked: {"lines": [8, 9, 10, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 28], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}
# gained: {"lines": [8, 12, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24, 25, 27, 29, 31, 32, 33, 34, 35, 37, 38, 39, 41], "branches": [[14, 0], [14, 15], [15, 16], [15, 38], [16, 14], [16, 19], [20, 21], [20, 31], [23, 24], [23, 27], [27, 29], [31, 16], [31, 32], [33, 31], [33, 34], [34, 35], [34, 37], [38, 39], [38, 41]]}

import os
from pathlib import Path
from isort.files import find
from isort.settings import Config


def test_find_directory_and_files(tmp_path: Path) -> None:
    # Create structure:
    # tmp_path/
    #   ├── skipped_dir/ (skipped by name in skip config)
    #   ├── normal_dir/
    #   │     ├── file.py (supported)
    #   │     └── file.txt (unsupported)
    #   ├── skipped_file.py (skipped via config or absolute path)
    #   └── normal_file.py (supported, passed directly or inside dir)

    skipped_dir = tmp_path / "skipped_dir"
    skipped_dir.mkdir()

    normal_dir = tmp_path / "normal_dir"
    normal_dir.mkdir()

    py_file = normal_dir / "file.py"
    py_file.write_text("print(1)")

    txt_file = normal_dir / "file.txt"
    txt_file.write_text("hello")

    direct_py = tmp_path / "normal_file.py"
    direct_py.write_text("print(2)")

    skipped_py = tmp_path / "skipped_file.py"
    skipped_py.write_text("print(3)")

    # Configure isort to skip by folder/file name so is_skipped matches correctly
    config = Config(
        skip=["skipped_dir", "skipped_file.py"],
    )

    skipped: list[str] = []
    broken: list[str] = []

    # Test paths containing:
    # 1. A directory (normal_dir + skipped_dir)
    # 2. A broken (non-existent) path
    # 3. A direct file path (normal_file.py)
    paths = [
        str(tmp_path),
        str(tmp_path / "non_existent_path.py"),
        str(direct_py),
        str(skipped_py),
    ]

    results = list(find(paths, config, skipped, broken))

    # Assertions
    assert str(py_file) in results
    assert str(txt_file) not in results  # unsupported filetype
    assert str(direct_py) in results
    assert str(skipped_dir) in skipped
    assert str(skipped_py) in skipped or os.path.abspath(skipped_py) in skipped
    assert str(tmp_path / "non_existent_path.py") in broken


def test_find_visited_dirs_symlink(tmp_path: Path) -> None:
    # Test directory symlink / visited_dirs branch if follow_links is True
    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()
    (real_dir / "sub.py").write_text("pass")

    link_dir = tmp_path / "link_dir"
    try:
        os.symlink(real_dir, link_dir, target_is_directory=True)
    except OSError:
        # Symlinks might not be supported on all platforms/environments (e.g. Windows without admin)
        return

    config = Config(follow_links=True)
    skipped: list[str] = []
    broken: list[str] = []

    results = list(find([str(tmp_path)], config, skipped, broken))
    # Should find sub.py via real_dir, but link_dir should hit resolved_path in visited_dirs and be pruned from dirnames
    assert len([r for r in results if r.endswith("sub.py")]) == 1
